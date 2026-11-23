# Publishing the Hugging Face Space

The Space is built from this repository's Dockerfile. It runs on the free CPU tier ("CPU basic"); it needs no GPU.

1. Create a Space under the Christian Pure account: SDK "Docker", hardware "CPU basic (free)".
2. In the Space's settings, add the variable `STUDY_SOURCE` = `huggingface`, so links back to christianpure.com are counted as coming from the Space.
3. Copy the whole repository into the Space's git repository, replacing README.md with `stores/huggingface/README.md` (Spaces read their settings from the front matter at the top of README.md).
4. Push. The Space builds the image and starts it on port 8417.
