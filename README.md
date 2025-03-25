# ArgumentMiningNOUs
Project in TDT 4310 - Intelligent Text Analytics and Language Understanding spring 2024
It is a collaborative effort by Nicolai Thorer Sivesind and Henrik Haug Larsen.

# Project overview
Natural language processing has in recent years seen massive advancements through the development and optimization of large language models. These advancements have opened new alleys into many segments of society for their application, both in terms of task complexity and performance. A group of researchers at the Institute of Social Science at the University of Oslo are now looking toward large language models for establishing new techniques for aiding in full-text analysis, which is an integral, but time-exhastive task. Until now, this has typically relied on well-established, but limited computational linguistic techniques. As part of a preliminary exploration before potentially launching a major interdisciplinary project in early 2025, they have tasked us, Nicolai Thorer Sivesind and Henrik Haug Larsen, with conducting a small study, to see how exploration of the problem-domain may be approached from the perspective of master students with competence in computer science.

## Project Process
1. *Build NOU Hearing dataset:*
    - Scrape NOU-hearing response documents from [NOU 2023: 25 webpage](https://www.regjeringen.no/no/dokumenter/horing-nou-2023-25-omstilling-til-lavutslipp-veivalg-for-klimapolitikken-mot-2050-rapport-av-klimautvalget-2050/id3009052/?expand=horingssvar)
    - Clean retrieved data 
    - Label data points by actor type according to national entity register, Brønnøysundregisteret

2. *Argument mine dataset using various approaches:*
    - Splitting by paragraph (metric baseline)
    - LDA-topic sentence similarity
    - Zero-shot in-context learning using LLAMA2 75B 

3. *Train and compare various multi-label classifiers for actor type classification across original and argument-mined datasets:*
    - Naive-Bayes classifier
    - Support Vector Machine Classifier
    - NB-Bert Sequence Classifier

# Dataset
The datasets are initially collected from "regjeringen.no" - "NOU 2023: 25 Omstilling til lavutslipp – Veivalg for klimapolitikken mot 2050".
It contains 4 datasets: "nou_hearings.csv" (split into paragraphs), "nou_hearings_full_text.csv", "cleaned_arguments_in_context_learning.csv", and "LDA_Arguments".

# Installation
The required packages to run the project is provided in requirements.txt and it will run on Python 3.12.2


Linke: [Final Report: NOU Hearing Response Text Analysis](https://github.com/Brilleslangen/ArgumentMiningNOUs/blob/master/NOU-Text-Analysis.pdf)
