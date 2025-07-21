# copy 100 segments to test_segments
mkdir -p input
ls segments | shuf | head -100 | xargs -I{} cp segments/{} input/

# run server
cd input
nohup python3 -m http.server 30002 > output.log 2>&1 &


# Run: 
python AgeDetection.py
nohup python AgeDetection.py > filename.out &

# Down file excel: 
scp ubuntu@103.253.20.30:/home/ubuntu/data/vietnamese/audio_long_output/classification_results.xlsx ~/Downloads/