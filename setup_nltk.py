import nltk

packages = [
    "punkt",
    "punkt_tab",
    "stopwords",
    "averaged_perceptron_tagger",
    "averaged_perceptron_tagger_eng",
    "maxent_ne_chunker",
    "maxent_ne_chunker_tab",
    "words",
    "wordnet",
]

for pkg in packages:
    nltk.download(pkg)

print("NLTK setup selesai!")