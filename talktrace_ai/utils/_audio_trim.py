"""Standalone audio trimmer — run with the noScribe engine venv's Python.

Writes the ``[start_ms, stop_ms]`` slice of ``src`` to ``dst`` as 16 kHz mono
PCM WAV (the format noScribe's own converter targets anyway). It exists to work
around a noScribe seek bug: ``ToWav.seek()`` computes
``stream.start_time * time_base``, which raises ``TypeError: unsupported operand
type(s) for *: 'NoneType' and 'Fraction'`` for streams whose ``start_time`` is
None (common for WAV). By pre-trimming here and handing noScribe a file that
needs no ``--start``/``--stop``, that buggy seek never runs.

Intentionally standalone — only ``av`` (present in the engine venv) plus the
stdlib, and **no noScribe import** — so the engine can execute it at arm's
length with the engine interpreter, exactly like it launches noScribe itself.

Usage:  python _audio_trim.py <src> <dst> <start_ms> <stop_ms>
        stop_ms == 0  ->  decode until the end.
Exit code 0 on success; non-zero (message on stderr) on failure.
"""
import sys


def trim(src, dst, start_ms, stop_ms):
    import av

    start_sec = max(0.0, start_ms / 1000.0)
    stop_sec = (stop_ms / 1000.0) if stop_ms and stop_ms > 0 else None

    container_in = av.open(src)
    try:
        stream_in = container_in.streams.audio[0]
        container_out = av.open(dst, mode="w", format="wav")
        try:
            # Same target format noScribe's ToWav uses (16 kHz mono PCM).
            stream_out = container_out.add_stream("pcm_s16le", rate=16000, layout="mono")

            if start_sec > 0:
                # Mirror noScribe's seek math, but treat a missing start_time
                # as 0 — the exact case noScribe fails to handle.
                tb = stream_in.time_base
                base_sec = float((stream_in.start_time or 0) * tb)
                seek_to = int((start_sec - base_sec) * tb.denominator)
                container_in.seek(max(0, seek_to), stream=stream_in)

            for frame in container_in.decode(stream_in):
                ft = frame.time
                if ft is not None:
                    # Seek lands on a keyframe before the target; drop the slack
                    # so the trim starts precisely.
                    if ft < start_sec - 0.05:
                        continue
                    if stop_sec is not None and ft > stop_sec:
                        break
                for packet in stream_out.encode(frame):
                    container_out.mux(packet)
            for packet in stream_out.encode(None):  # flush the encoder
                container_out.mux(packet)
        finally:
            container_out.close()
    finally:
        container_in.close()


def main():
    if len(sys.argv) != 5:
        sys.stderr.write("usage: _audio_trim.py <src> <dst> <start_ms> <stop_ms>\n")
        return 2
    src, dst = sys.argv[1], sys.argv[2]
    try:
        start_ms = int(sys.argv[3])
        stop_ms = int(sys.argv[4])
    except ValueError:
        sys.stderr.write("start_ms/stop_ms must be integers\n")
        return 2
    try:
        trim(src, dst, start_ms, stop_ms)
    except Exception as e:  # noqa: BLE001 — report any failure to the caller
        sys.stderr.write(f"trim failed: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
