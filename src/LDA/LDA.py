import pandas as pd
import spacy
from gensim import corpora, models
from gensim.corpora import Dictionary
from gensim.models import CoherenceModel
from matplotlib import pyplot as plt
from tqdm import tqdm

import sys
# sys.path.append('..')

from src.util.helpers import id2label


class LDA:
    def __init__(self, data: list[str], language, no_below=15, no_above=0.5, filter_extremes=True):
        """
        Initializes the LDA class with the provided data and configuration settings.

        Parameters:
            data (list[str]): List of documents as strings.
            no_below (int): Minimum number of documents a word must appear in to be kept.
            no_above (float): Maximum proportion of documents a word can appear in to be kept.
            language (str): The spaCy model to use for text processing.
        """
        self.data = data
        self.language = language
        self.nlp = spacy.load(language)
        self.preprocessed_data = self._preprocess()
        self.corpus, self.dictionary = self._build_corpus(no_below=no_below, no_above=no_above,
                                                          filter_extremes=filter_extremes)

    def _preprocess(self) -> list[list[str]]:
        """
        Cleans and extracts important words and noun phrases from the initial data.

        Returns:
            list[list[str]]: A list of documents where each document is a list of preprocessed tokens.
        """
        preprocessed = []

        for i, text in enumerate(self.data):
            if not isinstance(text, str):
                raise ValueError('Non-string value, Please Check data fields')

            doc = self.nlp(text)
            cleaned_noun_chunks = []

            for chunk in doc.noun_chunks:
                clean_chunk = ' '.join(
                    [token.lemma_.lower() for token in chunk if not token.is_stop and token.is_alpha])
                if clean_chunk:
                    cleaned_noun_chunks.append(clean_chunk)

            tokens = [token.lemma_.lower() for token in doc if not token.is_stop and token.is_alpha]
            combined = list(set(tokens + cleaned_noun_chunks))
            preprocessed.append(combined)

        return preprocessed

    def _build_corpus(self, no_below=15, no_above=0.5, filter_extremes=True):
        """
        Builds the corpus and dictionary from the preprocessed data using specified filtering parameters.

        Parameters:
            no_below (int): Minimum number of documents a word must appear in.
            no_above (float): Maximum proportion of documents a word can appear in.

        Returns:
            tuple: Contains the corpus (list of lists of (int, int) tuples) and the dictionary (gensim Dictionary).
        """
        dictionary = corpora.Dictionary(self.preprocessed_data)

        if filter_extremes:
            dictionary.filter_extremes(no_below=no_below, no_above=no_above, keep_n=100000)

        if not dictionary:
            raise ValueError("Empty dictionary generated from data")

        corpus = [dictionary.doc2bow(doc) for doc in self.preprocessed_data]

        if not any(corpus):
            raise ValueError("Empty corpus generated from dictionary")
        return corpus, dictionary

    def build_LDA_model(self, num_topics, passes):
        """
        Builds and returns an LDA model with the specified number of topics and passes.

        Parameters:
            num_topics (int): Number of topics for the LDA model.
            passes (int): Number of passes through the corpus during training.

        Returns:
            gensim.models.LdaModel: The trained LDA model.
        """
        lda_model = models.LdaModel(corpus=self.corpus, num_topics=num_topics, id2word=self.dictionary, passes=passes)
        return lda_model

    def predict_topics(self, model, relevancy=False):
        """
        Predicts the most relevant topics for the documents in the corpus using the specified model.

        Parameters:
            model (gensim.models.LdaModel): The LDA model used for prediction.
            relevancy (bool): If True, also returns relevant words from the topics for each document.

        Returns:
            list[dict]: List of dictionaries containing the topic and confidence of predictions, and optionally relevant words.
        """
        predictions = []
        for i, bow in enumerate(self.corpus):
            topic_distribution = model.get_document_topics(bow)
            sorted_topics = sorted(topic_distribution, key=lambda x: x[1], reverse=True)
            predictions.append(sorted_topics)

        return predictions

    def calculate_lda_model_coherences(self, topic_interval=(2, 12), passes=10):
        """
        Calculates the coherence scores for a range of topic numbers to evaluate LDA models.

        Parameters:
            topic_interval (tuple[int, int]): Start and end of the range of topics to test.
            passes (int): Number of passes through the corpus for each model.

        Returns:
            tuple: Contains the list of coherence values, the list of LDA models, and the topic range.
        """
        coherence_values = []
        model_list = []
        topic_range = range(topic_interval[0], topic_interval[1] + 1)

        for num_topics in tqdm(topic_range, 'Building LDA-models'):
            model = self.build_LDA_model(num_topics=num_topics, passes=passes)
            model_list.append(model)
            coherence_model = CoherenceModel(model=model, texts=self.preprocessed_data, dictionary=self.dictionary,
                                             coherence='c_v')
            coherence_values.append(coherence_model.get_coherence())

        return coherence_values, model_list, topic_range, passes

    def extract_arguments(self, dataframe, model, threshold):
        print(threshold)
        mined_arguments = []

        for _, row in tqdm(dataframe.iterrows(), desc="Processing Documents", total=len(dataframe)):
            actor = row['actor']
            document = row['text']
            label = row['label']

            doc = self.nlp(document)
            sentences = [sentence.text for sentence in doc.sents]
            predicted_topics = self.predict_topics(model)

            # Predict and Filter by threshold
            sentence_topics = [set([topic[0] for topic in sentence_predictions if topic[1] >= threshold])
                               for sentence_predictions in predicted_topics]

            # Find sequences of sentences with the same topic longer than two
            prev_topics = sentence_topics[0]
            topic_sequence = []
            for sentence, curr_topics in zip(sentences, sentence_topics):
                union = prev_topics.intersection(curr_topics)

                if union:
                    topic_sequence.append(sentence)
                else:  # If end of sequence
                    if len(topic_sequence) > 2:
                        arguments_text = ' '.join(topic_sequence)
                        row = {'actor': actor, 'text': arguments_text, 'label': label}
                        mined_arguments.append(row)

                    prev_topics = curr_topics
                    topic_sequence = [sentence]

            # Catch the last sequence in the document
            if len(topic_sequence) > 2:
                arguments_text = ' '.join(topic_sequence)
                row = {'actor': actor, 'text': arguments_text, 'label': label}
                mined_arguments.append(row)

        return pd.DataFrame(mined_arguments)


def plot_coherence_scores(topic_range, coherence_values, passes, savefig=None):
    """
    Plots coherence scores over a range of topic numbers to visualize the performance of LDA models.

    Parameters:
        topic_range (range): The range of topics over which coherence was computed.
        coherence_values (list[float]): The list of coherence scores corresponding to each topic in topic_range.
        passes (int): Number of passes through the corpus for each model used in coherence calculation.
        savefig (str, optional): Path to save the figure to. If None, the figure is shown but not saved.
    """
    plt.figure(figsize=(12, 6))
    plt.plot(topic_range, coherence_values, label=f'Passes: {passes}')
    plt.xlabel("Number of Topics")
    plt.ylabel("Coherence score")
    plt.title("Coherence Scores for LDA Models")
    plt.xticks(topic_range)
    plt.legend()

    if savefig:
        plt.savefig(savefig)
    plt.show()


def plot_topic_distribution(dataframe, savefig=None):
    """
    Plots the distribution of topics in the data, segmented by class.

    Parameters:
        dataframe (pandas.DataFrame): DataFrame containing topic predictions and class labels.
        savefig (str, optional): Filename to save the plot. If None, the plot is not saved.
    """
    dataframe['label'] = dataframe['label'].apply(id2label)
    dataframe['topic'] = dataframe['topic_predictions'].apply(lambda x: x[0][0])
    grouped = dataframe.groupby(['topic', 'label']).size().unstack(fill_value=0)

    class_totals = grouped.sum()  # Frequency of each class
    grouped_percentage = grouped.div(class_totals) * 100

    # Plotting the stacked bar chart with percentages
    ax = grouped_percentage.plot(kind='bar', stacked=True, figsize=(10, 7))
    plt.title('Percentage Distribution of Topics Segmented by Class Relative to Class Total')
    plt.xlabel('Topic')
    plt.ylabel('Percentage')
    plt.xticks(rotation=0)
    plt.legend(title='Class')

    for c in ax.containers:
        ax.bar_label(c, fmt='%.1f%%', label_type='center')

    if savefig:
        plt.savefig(f'../../plots/{savefig}.png')

    plt.show()
