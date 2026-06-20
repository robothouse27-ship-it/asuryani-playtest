#!/usr/bin/env bash
# OCR the image-only AoD core Rulebook into ocr_cache/ (chunked, ~18 min).
set -uo pipefail; cd "$(dirname "$0")/.."
export OMP_NUM_THREADS=2
pdf="HH 30 AoD Rulebook Raw 2.pdf"; pages=362; n=8; per=$(( (pages+n-1)/n )); pids=()
for ((c=0;c<n;c++)); do
  s=$(( c*per+1 )); e=$(( (c+1)*per )); (( e>pages )) && e=$pages; (( s>pages )) && break
  python3 build/ocr_liber.py "$pdf" "/tmp/core_chunk${c}.txt" "$s" "$e" >/dev/null 2>&1 &
  pids+=($!)
done
for p in "${pids[@]}"; do wait "$p"; done
cat /tmp/core_chunk*.txt > ocr_cache/aod_rulebook_ocr.txt; rm -f /tmp/core_chunk*.txt
echo "DONE core: $(grep -c 'PDF PAGE' ocr_cache/aod_rulebook_ocr.txt) pages -> ocr_cache/aod_rulebook_ocr.txt"
