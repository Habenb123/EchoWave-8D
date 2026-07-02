import subprocess

def separate_song(input_file, output_dir="separated"):
    subprocess.run(
        [
            "demucs",
            input_file,
            "-o",
            output_dir
        ],
        check=True
    )