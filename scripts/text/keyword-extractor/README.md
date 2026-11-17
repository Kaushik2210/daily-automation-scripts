# keyword-extractor

## Purpose
List what each document is mainly about. The tool counts the meaningful words in every text or markdown file (dropping common words such as "the" and "with") and shows the most frequent ones. When you give it several documents it weights the words so that terms found in every document rank lower and words special to one document rank higher (a simple TF-IDF), which is exactly what you want for tagging a folder of notes or articles.

## Install
Standard library only, Python 3.11+. Nothing to install.

## Usage
```bash
python keyword_extractor.py FILE_OR_FOLDER [...] [--top 8] [--phrases]
```
Folders are searched recursively for `.txt`, `.md`, `.markdown` and `.rst` files. `--top` sets how many keywords to show per document. `--phrases` looks for repeated two-word phrases ("wind turbines") instead of single words.

## Example
```bash
python keyword_extractor.py articles/ --top 4
```
```
batteries.txt  (23 words)
    batteries                x2
    battery                  x1
    changes                  x1
    falling                  x1
solar.txt  (25 words)
    solar                    x4
    panels                   x2
    cheaper                  x1
    evening                  x1
wind.txt  (26 words)
    wind                     x5
    farms                    x2
    air                      x1
    blows                    x1

Keywords are weighted so that words found in every document rank lower.
```

## Notes
- Words must be at least three letters long; numbers are ignored.
- The ranking is by weighted score, the count (`x3`) shows how often the word appears.
- Use `word-counter` for a plain frequency table and `text-summarizer` for the key sentences.
