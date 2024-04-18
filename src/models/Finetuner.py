import os
from typing import Union, List

import evaluate
import numpy as np
import pandas as pd
import torch
import wandb
from datasets import Dataset, DatasetDict
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    Trainer,
    TrainingArguments, pipeline,
)

torch.manual_seed(seed=42)


def select_device():
    if torch.backends.mps.is_available():
        return torch.device("mps")
    elif torch.cuda.is_available():
        return torch.device("cuda")
    else:
        return torch.device("cpu")


class FineTuner:
    def __init__(self, model_name: str, csv_path: str, output_name: str,
                 num_epochs: int = 5,
                 max_tokenized_length: int = 512,
                 metric_names: tuple = tuple('accuracy'),
                 wand_logging: bool = True,
                 eval_steps: int = 50):
        # Run time constants
        self.max_tokenized_length = max_tokenized_length
        self.num_epochs = num_epochs
        self.seed = 42
        self.metric_names = metric_names
        self.wandb_logging = wand_logging
        self.eval_steps = eval_steps
        self.output_name = output_name

        # Load dataset
        self.dataset, self.labels, self.label2id, self.id2label = self.load_dataset_from_csv(csv_path)

        # Initialize tokenizer and model
        self.tokenizer = AutoTokenizer.from_pretrained(model_name)
        self.model = AutoModelForSequenceClassification.from_pretrained(
            model_name, num_labels=len(self.labels),
            id2label=self.id2label,
            label2id=self.label2id)

        # Initialize trainer
        self.trainer = self.init_trainer(self.dataset)
        self.classifier = pipeline("text-classification", model=self.model, tokenizer=self.tokenizer)

        # Initialize Weights and Biases
        if self.wandb_logging:
            self.wandb = wandb.init(project="TDT4310-NLP",
                                    config={
                                        'base_model': model_name,
                                        'dataset': self.dataset['train'].config_name,
                                        'train_dataset_size': len(self.dataset['train']),
                                        'eval_dataset_size': len(self.dataset['test']),
                                        'max_tokenized_length': self.max_tokenized_length,
                                    })
        else:
            os.environ["WANDB_DISABLED"] = "true"

    def load_dataset_from_csv(self, csv_path, test_size=0.1):
        """
        Loads a dataset from a CSV file, preprocesses it, and splits it into training and test sets.

        Args:
            self (str): The file path to the CSV file containing the dataset.
            test_size (float): The proportion of the dataset to include in the test split.

        Returns:
            DatasetDict: A dictionary containing 'train' and 'test' datasets.
        """
        # Load data from CSV
        df = pd.read_csv(csv_path)
        df = df[['text', 'label']].dropna()
        full_dataset = Dataset.from_pandas(df)
        labels = sorted(list(set(full_dataset['label'])))

        # Convert labels to integers
        label2id = {label: i for i, label in enumerate(labels)}
        id2label = {i: label for i, label in enumerate(labels)}
        full_dataset = full_dataset.map(lambda dp: {'label': label2id[dp['label']]})

        # Split dataset into train and test
        train_test_split = full_dataset.train_test_split(shuffle=False, test_size=test_size)
        return train_test_split, labels, label2id, id2label

    def compute_metrics(self, eval_pred):
        """Function for computing evaluation metrics"""
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)

        metrics = {}

        for metric in self.metric_names:
            if metric == 'accuracy':
                metrics[metric] = evaluate.load(metric).compute(
                    predictions=predictions, references=labels)[metric]
            else:
                metrics[metric] = evaluate.load(metric).compute(
                    predictions=predictions, references=labels, average='macro')[metric]

        return metrics

    def tokenize_function(self, examples):
        return self.tokenizer(
            text=examples["text"],
            padding=True,
            truncation=True,
            max_length=self.max_tokenized_length,
            return_tensors="pt")

    def init_trainer(self, dataset: Dataset):
        tokenized_datasets = dataset.map(self.tokenize_function, batched=True)
        train_dataset = tokenized_datasets["train"]
        test_dataset = tokenized_datasets["test"]

        print(train_dataset[0:3])
        print(test_dataset[1])

        training_args = TrainingArguments(
            output_dir=os.path.join("../../classifiers", self.output_name),
            evaluation_strategy="steps",
            eval_steps=self.eval_steps,
            save_strategy='steps',
            optim='adamw_torch',
            num_train_epochs=self.num_epochs,
            auto_find_batch_size=True,
            metric_for_best_model='accuracy'
        )
        return Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics,
        )

    def classify(self, text):
        # Initialize pipeline
        return self.classifier(text)

    def load_model(self, model_path):
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.trainer.model = self.model

    def predict(self, data: Union[str, List[str]]) -> torch.Tensor:
        """
        Generates a prediction for the data and returns probabilities as a tensor.
        """
        encoding = self.tokenizer(data, return_tensors="pt", padding="max_length", truncation=True)
        input_ids = encoding['input_ids'].to(self.device)

        with torch.no_grad():
            self.model.to(self.device)
            outputs = self.model(input_ids)
            logits = outputs.logits

            # Ensure batch size is handled correctly
            if logits.dim() == 1:
                logits = logits.unsqueeze(0)
            probabilities = torch.softmax(logits, dim=-1)

        return probabilities

    def train(self):
        self.trainer.train()

    def evaluate(self):
        print(self.dataset["test"])
        return self.trainer.evaluate()
