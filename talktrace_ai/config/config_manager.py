import ast
import configparser
import json
import os
import re
from pathlib import Path


# Single source of truth for the provider list. Order matters: the first
# entry is both the default sort in the model dropdown AND the fallback
# ``get_current_api`` snaps to when a saved config points at a disabled
# provider.
#
# *** LocalMind-first configuration (July 2026) ***
# LocalMind (api.lminference.eu) is an EU-hosted, OpenAI-compatible inference
# gateway; because it keeps classroom transcripts inside the EU it is the
# GDPR-conformant default and leads the list. Alongside it: OpenAI + Anthropic
# (closed, US-hosted), Mistral (EU-hosted) and DeepSeek (frontier-class quality
# at a fraction of OpenAI cost). Groq, Ollama and OpenRouter are intentionally
# **commented out** rather than deleted — their SDK clients in llm_clients.py
# remain in place so they can be re-enabled in a single-line change.
#
# Adding a provider back: uncomment its slug here and re-enable the entry in
# the two ``_provider_choices`` dropdowns (handlers/options.py and
# handlers/sidebar/_model_select.py).
KNOWN_PROVIDERS = [
    'localmind',    # EU-hosted gateway — default provider (GDPR-conformant)
    'openai',
    # 'groq',       # disabled (May 2026)
    'anthropic',
    # 'ollama',     # disabled (May 2026); also disables local-only mode
    # 'openrouter', # disabled (May 2026)
    'mistral',
    'deepseek',
]


# --- Custom providers -----------------------------------------------------
# Users can register **any number** of their own OpenAI-compatible endpoints
# (self-hosted vLLM/llama.cpp, institutional gateways, …). Each carries a
# user-chosen name, a base URL and its own key in the OS keyring. Internally a
# custom provider is addressed by the composite slug ``custom:<id>`` — the
# ``id`` is a filesystem/config-safe slug derived from the name. The registry
# itself lives in the ``[CUSTOM_PROVIDERS]`` config section (JSON), the model
# lists under ``MODELS.custom_<id>_models`` (a colon in a configparser option
# name collides with the ``:`` key/value delimiter, so the slug's colon is
# swapped for an underscore in the models key only). Keyring username follows
# the same formula as the built-ins: ``api_key_<slug>`` → ``api_key_custom:<id>``.
CUSTOM_PREFIX = 'custom:'


def is_custom_provider(slug) -> bool:
    """True for a ``custom:<id>`` provider slug."""
    return isinstance(slug, str) and slug.startswith(CUSTOM_PREFIX)


def custom_provider_id(slug):
    """The ``<id>`` part of a ``custom:<id>`` slug, else ``None``."""
    return slug[len(CUSTOM_PREFIX):] if is_custom_provider(slug) else None


def custom_provider_slug(pid) -> str:
    """Compose the ``custom:<id>`` slug for a custom-provider id."""
    return f'{CUSTOM_PREFIX}{pid}'


class ConfigManager:
    def __init__(self):
        self.config = configparser.ConfigParser()
        self.config_dir = Path(__file__).parent
        self.config_file = self.config_dir / 'config.ini'
        self.default_config = self.config_dir / 'default_config.ini'
        
        # Ensure required sections exist
        self.required_sections = ['PROMPTS', 'MODELS', 'ADVANCED']
        
        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Set by migrate_legacy_custom() when it moves the single legacy custom
        # provider into the registry — signals the key loader to migrate the
        # keyring entry too. Transient (per-instance), never persisted.
        self._legacy_custom_key_id = None

        # Load or create config file
        self._load_or_create_config()


    def _load_or_create_config(self):
        if not self.config_file.exists():
            # Copy default config if exists
            if self.default_config.exists():
                with open(self.default_config, 'r', encoding='utf-8') as f:
                    self.config.read_file(f)
            else:
                # Initialize with empty sections if no default config
                for section in self.required_sections:
                    self.config.add_section(section)
            # Save new config file
            self.save_config()
        else:
            self.config.read(self.config_file, encoding='utf-8')
            # Ensure all required sections exist
            for section in self.required_sections:
                if not self.config.has_section(section):
                    self.config.add_section(section)
            self._migrate_missing_keys()
        # Fold a pre-existing single custom endpoint into the new registry
        # (idempotent — a no-op once migrated or on a fresh install).
        self.migrate_legacy_custom()

    def _migrate_missing_keys(self):
        """Copy keys from default_config.ini that the user's config.ini is
        missing (e.g. after adding language-qualified prompt variants)."""
        if not self.default_config.exists():
            return
        defaults = configparser.ConfigParser()
        with open(self.default_config, 'r', encoding='utf-8') as f:
            defaults.read_file(f)
        changed = False
        for section in defaults.sections():
            if not self.config.has_section(section):
                self.config.add_section(section)
            for key, value in defaults.items(section):
                if not self.config.has_option(section, key):
                    self.config.set(section, key, value)
                    changed = True
        if changed:
            self.save_config()


    def save_config(self):
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, 'w', encoding='utf-8') as f:
            self.config.write(f)


    def _prompt_key(self, prompt_type, language):
        # prompt_type in {'system', 'user', 'system_default', 'user_default'}
        base, _, suffix = prompt_type.partition('_')  # ('system', '_', 'default') or ('system', '', '')
        lang_part = f'_{language}' if language in ('de', 'en') else ''
        return f'{base}_prompt{lang_part}{"_" + suffix if suffix else ""}'

    def get_prompts(self, language=None):
        if not self.config.has_section('PROMPTS'):
            self.config.add_section('PROMPTS')

        if language is None:
            language = self.get_localization().get('current_language', 'de')

        def _read(prompt_type):
            # Prefer language-qualified key; fall back to unqualified (legacy DE) key.
            lang_key = self._prompt_key(prompt_type, language)
            legacy_key = self._prompt_key(prompt_type, None)
            val = self.config.get('PROMPTS', lang_key, fallback=None)
            if val is None or val == '':
                val = self.config.get('PROMPTS', legacy_key, fallback='')
            return val

        return {
            'system': _read('system'),
            'system_default': _read('system_default'),
            'user': _read('user'),
            'user_default': _read('user_default'),
        }


    def set_prompt(self, prompt_type, text, language=None):
        if prompt_type not in ['system', 'user', 'system_default', 'user_default']:
            raise ValueError("Prompt type must be either 'system','user', 'system_default' or 'user_default'")

        if not self.config.has_section('PROMPTS'):
            self.config.add_section('PROMPTS')

        if language is None:
            language = self.get_localization().get('current_language', 'de')

        self.config.set('PROMPTS', self._prompt_key(prompt_type, language), text)
        self.save_config()

    ### Model List Retrieval and Manipulation Methods ###
    @staticmethod
    def _is_local_model(provider, entry) -> bool:
        """A model counts as local-only if (a) the entry carries an explicit
        ``local: true`` flag, or (b) it sits under the ollama provider AND
        the name doesn't end with ``cloud``. The suffix heuristic catches
        both ``glm-5.1:cloud`` and ``gemma4:31b-cloud`` style names that
        Ollama Cloud uses, so users who flip "local only" don't accidentally
        hit a cloud endpoint even on configs that pre-date the flag.
        """
        if isinstance(entry, dict) and "local" in entry:
            return bool(entry["local"])
        if provider != "ollama":
            return False
        name = ((entry.get("name") if isinstance(entry, dict) else "") or "").lower()
        return not name.endswith("cloud")

    def get_models(self, provider=None, local_only=False):
        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        def _filter(prov, entries):
            if not local_only:
                return entries
            return [v for v in entries if self._is_local_model(prov, v)]

        if provider:
            models = self.config.get('MODELS', self._models_key(provider), fallback='[]')
            return [v["name"] for v in _filter(provider, ast.literal_eval(models))]
          # Convert string representation to list
        else:
            # Return all models combined (built-ins + registered custom providers)
            all_models = []
            for p in self.all_providers():
                entries = ast.literal_eval(self.config.get('MODELS', self._models_key(p), fallback='[]'))
                all_models += _filter(p, entries)
            return [v["name"] for v in all_models]


    def set_models(self, provider, models):
        if provider not in KNOWN_PROVIDERS and not is_custom_provider(provider):
            raise ValueError(f"Provider must be one of {KNOWN_PROVIDERS} or a custom:<id> slug")

        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        self.config.set('MODELS', self._models_key(provider), str(models))
        self.save_config()


    def add_model(self, provider, model_name, input_cost, output_cost, local=None):
        """
        Adds a new model to the provider's model list in the config.
        Example:
            self.add_model("openai", "gpt-6", 0.007, 0.014)
            self.add_model("ollama", "llama3:8b", 0, 0, local=True)

        ``local`` defaults to True for non-cloud Ollama models (no ``:cloud``
        suffix) and False for everything else. Pass an explicit bool to
        override.
        """
        if provider not in KNOWN_PROVIDERS and not is_custom_provider(provider):
            raise ValueError(f"Provider must be one of {KNOWN_PROVIDERS} or a custom:<id> slug")

        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        key = self._models_key(provider)

        # Safely load the existing models
        try:
            current_models = ast.literal_eval(self.config.get('MODELS', key, fallback='[]'))
        except Exception:
            current_models = []

        # Check if model already exists
        if any(m['name'] == model_name for m in current_models):
            print(f"Model '{model_name}' already exists for provider '{provider}'. Skipping.")
            return

        if local is None:
            # Default heuristic: only Ollama with non-:cloud suffix is local.
            local = (provider == "ollama"
                     and not model_name.lower().endswith(":cloud"))

        # Append the new model
        current_models.append({
            "name": model_name,
            "input": input_cost,
            "output": output_cost,
            "local": bool(local),
        })

        # Save back to config
        self.set_models(provider, current_models)

    def remove_model(self, model_names):
        """
        Removes one or more models from the config for both providers (openai/groq).
        Example:
            self.remove_model("gpt-4o")
            self.remove_model(["gpt-5", "deepseek-r1-distill-llama-70b"])
        """
        if not isinstance(model_names, list):
            model_names = [model_names]

        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        for provider in self.all_providers():
            key = self._models_key(provider)

            # Load current models safely
            try:
                current_models = ast.literal_eval(self.config.get('MODELS', key, fallback='[]'))
            except Exception:
                current_models = []

            # Filter out models whose 'name' matches any in model_names
            updated_models = [m for m in current_models if m['name'] not in model_names]

            # Only update if something actually changed
            if len(updated_models) != len(current_models):
                self.set_models(provider, updated_models)
                print(f"[OK] Removed models from '{provider}': {', '.join(set(model_names) - {m['name'] for m in updated_models})}")

        # Persist changes
        self.save_config()

                
    
    def reset_models(self):
        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        for provider in KNOWN_PROVIDERS:
            self.config.set('MODELS', f'{provider}_models', self.config.get('MODELS', f'{provider}_models_default', fallback='[]'))
        self.save_config()

    ### Current Model and API Management Methods ###    
    def get_current_model(self):
        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')
        return self.config.get('MODELS', 'current_model', fallback=None)
    

    def set_current_model(self, model_name):
        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')
        self.config.set('MODELS', 'current_model', model_name)
        self.save_config()


    def get_current_api(self):
        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')
        api = self.config.get('MODELS', 'current_api', fallback="localmind")
        # Migration guard: a user's saved config may still point at a provider
        # we have since disabled (e.g. ``openrouter`` from the OpenRouter test
        # phase). Snap back to the first known provider silently — otherwise
        # downstream ``set_current_api`` validation would refuse to round-trip
        # the value and the UI would land on a broken default.
        # ``KNOWN_PROVIDERS[0]`` is LocalMind (the EU-hosted default). A custom
        # slug is valid only while its registry entry still exists — a deleted
        # custom provider snaps back to the default the same way.
        valid = api in KNOWN_PROVIDERS or (
            is_custom_provider(api) and self.get_custom_provider(api) is not None)
        if not valid:
            print(f"[config] current_api={api!r} not available — migrating to {KNOWN_PROVIDERS[0]!r}")
            api = KNOWN_PROVIDERS[0]
            self.config.set('MODELS', 'current_api', api)
            self.save_config()
        return api


    def set_current_api(self, provider):
        if provider not in KNOWN_PROVIDERS and not is_custom_provider(provider):
            raise ValueError(f"Provider must be one of {KNOWN_PROVIDERS} or a custom:<id> slug")

        if not self.config.has_section('MODELS'):
            self.config.add_section('MODELS')

        self.config.set('MODELS', 'current_api', provider)
        self.save_config()
        
    ### Custom-Provider Registry ###
    # Any number of user-registered OpenAI-compatible endpoints, each a dict
    # ``{"id", "name", "base_url"}`` (the migrated legacy one also carries
    # ``"from_legacy": true``). Stored as a JSON list in [CUSTOM_PROVIDERS].
    def _load_custom_providers(self):
        if not self.config.has_section('CUSTOM_PROVIDERS'):
            return []
        raw = self.config.get('CUSTOM_PROVIDERS', 'providers', fallback='[]')
        try:
            data = json.loads(raw)
        except Exception:
            return []
        return [e for e in data if isinstance(e, dict) and e.get('id')] if isinstance(data, list) else []

    def _save_custom_providers(self, providers):
        if not self.config.has_section('CUSTOM_PROVIDERS'):
            self.config.add_section('CUSTOM_PROVIDERS')
        self.config.set('CUSTOM_PROVIDERS', 'providers',
                        json.dumps(providers, ensure_ascii=False))
        self.save_config()

    def list_custom_providers(self):
        """All registered custom providers (list of ``{id, name, base_url}``)."""
        return self._load_custom_providers()

    def get_custom_provider(self, pid):
        """The registry entry for a custom-provider id (or slug), else ``None``."""
        pid = custom_provider_id(pid) or pid
        for e in self._load_custom_providers():
            if e.get('id') == pid:
                return e
        return None

    def custom_base_url(self, provider):
        """Base URL of a custom provider (accepts slug or bare id), '' if unknown."""
        e = self.get_custom_provider(provider)
        return (e or {}).get('base_url', '').strip()

    def _slugify_custom_id(self, name, existing):
        base = re.sub(r'[^a-z0-9]+', '-', (name or '').strip().lower()).strip('-') or 'provider'
        pid = base
        i = 2
        while pid in existing:
            pid = f'{base}-{i}'
            i += 1
        return pid

    def add_custom_provider(self, name, base_url):
        """Register a new custom provider; returns its generated id."""
        providers = self._load_custom_providers()
        pid = self._slugify_custom_id(name, {e['id'] for e in providers})
        providers.append({
            'id': pid,
            'name': (name or '').strip() or pid,
            'base_url': (base_url or '').strip().rstrip('/'),
        })
        self._save_custom_providers(providers)
        return pid

    def update_custom_provider(self, pid, *, name=None, base_url=None):
        pid = custom_provider_id(pid) or pid
        providers = self._load_custom_providers()
        for e in providers:
            if e.get('id') == pid:
                if name is not None:
                    e['name'] = name.strip() or e['id']
                if base_url is not None:
                    e['base_url'] = base_url.strip().rstrip('/')
                self._save_custom_providers(providers)
                return True
        return False

    def remove_custom_provider(self, pid):
        """Drop a custom provider and its stored model list. Returns True if removed."""
        pid = custom_provider_id(pid) or pid
        providers = self._load_custom_providers()
        remaining = [e for e in providers if e.get('id') != pid]
        if len(remaining) == len(providers):
            return False
        key = f'custom_{pid}_models'
        if self.config.has_section('MODELS') and self.config.has_option('MODELS', key):
            self.config.remove_option('MODELS', key)
        self._save_custom_providers(remaining)
        return True

    def all_providers(self):
        """Built-in providers plus every registered custom slug (``custom:<id>``)."""
        return list(KNOWN_PROVIDERS) + [
            custom_provider_slug(e['id']) for e in self._load_custom_providers()
        ]

    def _models_key(self, provider):
        """Config option name holding a provider's model list. Custom slugs use
        an underscore (configparser treats ``:`` as a key/value delimiter)."""
        if is_custom_provider(provider):
            return f'custom_{custom_provider_id(provider)}_models'
        return f'{provider}_models'

    def migrate_legacy_custom(self):
        """Fold a pre-registry single custom endpoint into the registry.

        Older configs stored one endpoint in ``[CUSTOM] base_url`` + model list
        under ``MODELS.custom_models`` + keyring ``api_key_custom``. Move all
        three into a first registry entry (marked ``from_legacy``), then clear
        the legacy config so this runs exactly once. Idempotent and safe on a
        fresh install (nothing to migrate)."""
        legacy_url = ''
        if self.config.has_section('CUSTOM'):
            legacy_url = self.config.get('CUSTOM', 'base_url', fallback='').strip()
        legacy_models = ''
        if self.config.has_section('MODELS'):
            legacy_models = self.config.get('MODELS', 'custom_models', fallback='').strip()
        has_models = legacy_models not in ('', '[]')
        if not legacy_url and not has_models:
            return  # nothing to migrate (fresh install or already done)
        providers = self._load_custom_providers()
        if any(e.get('from_legacy') for e in providers):
            return  # already migrated in a previous run
        pid = self._slugify_custom_id('Custom endpoint', {e['id'] for e in providers})
        providers.append({
            'id': pid,
            'name': 'Custom endpoint',
            'base_url': legacy_url.rstrip('/'),
            'from_legacy': True,
        })
        self._save_custom_providers(providers)  # persists
        if has_models:
            self.config.set('MODELS', f'custom_{pid}_models', legacy_models)
        # Clear the legacy markers so a re-run is a no-op.
        if self.config.has_section('CUSTOM'):
            self.config.set('CUSTOM', 'base_url', '')
        if self.config.has_option('MODELS', 'custom_models'):
            self.config.remove_option('MODELS', 'custom_models')
        # Best-effort keyring copy so the existing key keeps working.
        try:
            import keyring
            old = keyring.get_password('talktrace', 'api_key_custom')
            if old:
                keyring.set_password('talktrace', f'api_key_custom:{pid}', old)
        except Exception:
            pass
        self.save_config()
        self._legacy_custom_key_id = pid

    ### Parameter Management Methods ###
    def get_parameters(self):
        if not self.config.has_section('PARAMETERS'):
            self.config.add_section('PARAMETERS')
        return {
            'teacher_name': self.config.get('PARAMETERS', 'teacher_name', fallback='LEHRER'),
            'teacher_name_options': self.config.get('PARAMETERS', 'teacher_name', fallback='LEHRER'),
            'group_id': self.config.get('PARAMETERS', 'group_id', fallback='Neo'),
            'num_pupils': self.config.getint('PARAMETERS', 'num_pupils', fallback=25),
            'teacher_name_default': self.config.get('PARAMETERS', 'teacher_name_default', fallback='LEHRER'),
            'group_id_default': self.config.get('PARAMETERS', 'group_id_default', fallback='Neo'),
            'num_pupils_default': self.config.getint('PARAMETERS', 'num_pupils_default', fallback=25)
        }
    
    
    def set_parameter(self, key, value):
        if key not in ['teacher_name', 'teacher_name_options', 'group_id', 'num_pupils']:
            raise ValueError("Parameter key must be either 'teacher_name', 'teacher_name_options', 'group_id' or 'num_pupils'")
        
        if not self.config.has_section('PARAMETERS'):
            self.config.add_section('PARAMETERS')
            
        self.config.set('PARAMETERS', key, str(value))
        self.save_config()

    ### Localization Management Methods ###
    def get_localization(self):
        if not self.config.has_section('LOCALIZATION'):
            self.config.add_section('LOCALIZATION')
        return {
            'default_language': self.config.get('LOCALIZATION', 'default_language', fallback='en'),
            'current_language': self.config.get('LOCALIZATION', 'current_language', fallback='en'),
            'default_language_default': self.config.get('LOCALIZATION', 'default_language_default', fallback='en'),
            'current_language_default': self.config.get('LOCALIZATION', 'current_language_default', fallback='en'),
        }
    

    def set_localization(self, key, value):
        if value not in ['de', 'en']:
            raise ValueError("Localization must be either 'de' or 'en'")
        if key not in ['default_language', 'current_language']:
            raise ValueError("Localization must be either 'de' or 'en'")
        
        if not self.config.has_section('LOCALIZATION'):
            self.config.add_section('LOCALIZATION')
            
        self.config.set('LOCALIZATION', key, str(value))
        self.save_config()

    ### Advanced Settings (Streaming Toggle, etc.) ###
    def get_advanced(self):
        if not self.config.has_section('ADVANCED'):
            self.config.add_section('ADVANCED')
        return {
            'streaming': self.config.getboolean('ADVANCED', 'streaming', fallback=False),
            'streaming_default': self.config.getboolean('ADVANCED', 'streaming_default', fallback=False),
            'local_only': self.config.getboolean('ADVANCED', 'local_only', fallback=False),
            'local_only_default': self.config.getboolean('ADVANCED', 'local_only_default', fallback=False),
        }

    def set_advanced(self, key, value):
        if key not in ['streaming', 'local_only']:
            raise ValueError("Advanced key must be 'streaming' or 'local_only'")
        if not self.config.has_section('ADVANCED'):
            self.config.add_section('ADVANCED')
        self.config.set('ADVANCED', key, 'true' if bool(value) else 'false')
        self.save_config()

    ### Pricing Prediction Helper Method ###
    def get_api_pricing(self):
        """Returns pricing for different APIs and models"""
        pricing = {}
        for provider in self.all_providers():
            key = self._models_key(provider)
            models_str = self.config.get('MODELS', key, fallback='[]')
            try:
                models = ast.literal_eval(models_str)  # convert to list of dicts
            except Exception:
                models = []

            # Build dictionary of model: {input, output}
            provider_pricing = {
                m['name']: {'input': m['input'], 'output': m['output']}
                for m in models if all(k in m for k in ('name', 'input', 'output'))
            }

            pricing[provider] = provider_pricing

        return pricing
