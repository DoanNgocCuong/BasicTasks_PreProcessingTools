# copy 100 segments to test_segments
mkdir -p input
ls segments | shuf | head -100 | xargs -I{} cp segments/{} input/

# run server
cd input
nohup python3 -m http.server 30002 > output.log 2>&1 &