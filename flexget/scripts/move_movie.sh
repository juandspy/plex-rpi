#!/bin/bash -e
# A script to manually move a movie from the /downloads folder to the 
# /storage/movies. This is useful when there is any issue with FlexGet not
#  being able to run the sort_movies task.
#
# Usage:
#  $ ./move_movie.sh -p MOVIE_PATH -n MOVIE_NAME -y MOVIE_YEAR


while getopts p:n:y: flag
do
    case "${flag}" in
        p) location=${OPTARG};;
        n) movie_name=${OPTARG};;
        y) movie_year=${OPTARG};;
    esac
done

echo "[DEBUG] Movie path: $location";
echo "[DEBUG] Movie name: $movie_name";
echo "[DEBUG] Movie year: $movie_year";

filename=$(basename -- "$location")
extension="${filename##*.}"
output_folder="/storage/movies/${movie_name} (${movie_year})"
output_path="${output_folder}/${movie_name} (${movie_year}).${extension}"

echo "[DEBUG] Creating folder: ${output_folder}"
mkdir -p "${output_folder}"

echo "[DEBUG] Output file: ${output_path}"
if mediainfo "${location}" | grep EAC3; then
    echo "[DEBUG] Movie is encoded with EAC3, optimizing"
    ffmpeg -hwaccel auto -y -i "${location}" -map 0 -c:s copy -c:v copy -c:a ac3 -b:a 640k "${output_path}"
else
    cp "${location}" "${output_path}"
fi

echo "[DEBUG] Done"