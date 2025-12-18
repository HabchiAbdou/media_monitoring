import re
import os
import math
import bisect
import logging
import itertools
from DarijaDistance.mappings import Mappings
from DarijaDistance.data_loader import DataLoader
from collections import OrderedDict

logging.basicConfig(level=logging.WARNING)

class WordDistance:
    def __init__(self, sum_threshold=100, distance_threshold=10, acceptance_threshold=20, max_words=3):
        """Initialize the WordDistance class.
        The class loads the necessary data files and mappings to calculate the distance between words.

        The class loads the following files:

        - hash_table_word.pickle: A dictionary containing the positional encoding and sum image of each word (key = word).
        Example:
            'noDi': [{'translation': 'get up', 'positional_encoding': '970120940110', 'sum_encoding': 2140}]
        
        - hash_table_sum.pickle: A dictionary containing the words grouped by their sum image (key = sum representation).
        Example:
            2950: [ {'darija': '3ber', 'translation': 'he measured', 'positional_encoding': '928934115973'},
                    {'darija': '8rrs', 'translation': 'he broke', 'positional_encoding': '983973973992'}]
        
        - list_of_sum_keys.pickle: list of the represented numbers (sums), sorted, to speed up the search

        - The class also loads the exact translations from the CSV file 'translations.csv' and the list of names from the CSV file 'names.csv'.

        Example:
            >>> wd = WordDistance()
            >>> wd.get_positional("la")
            ('40001', 41)
        """
        # Get the directory where the current script resides
        base_dir = os.path.dirname(os.path.abspath(__file__))
        loader = DataLoader(base_dir)

        # Define the file names and their corresponding attributes
        self.hash_table_word = loader.load_pickle('hash_table_word.pickle')
        self.hash_table_sum = loader.load_pickle('hash_table_sum.pickle')
        self.list_of_sum_keys = loader.load_pickle('list_of_sum_keys.pickle')

        # Initialize mappings
        mappings = Mappings()
        self.mapping = mappings.get_mapping()

        # Load exact translations from the CSV file
        self.exact = loader.load_translations()  # Load exact translations
        self.names = loader.load_names()  # Load names

        # Initialize thresholds and limits
        self.sum_threshold = sum_threshold
        self.distance_threshold = distance_threshold
        self.acceptance_threshold = acceptance_threshold
        self.max_words = max_words

        logging.info("WordDistance initialized successfully with base directory: %s", base_dir)

    def get_positional(self, word):
        """Returns positional encoding and sum image of input words.
        The positional encoding is a concatenation of the mappings of the letters in the word.
        The sum image is the sum of the mappings of the letters in the word.
        Args:
            word (str): The word to encode.
        Returns:
            tuple: A tuple containing the positional encoding and the sum image of the word.
        
        Example:
            >>> get_positional("la")
            ('40003', 43)
        """
        logging.info("[get_positional] - Getting positional encoding and sum image for word: %s", word)
        if type(word) is not str:
            return word
        positional = ""
        sum_image = 0
        last = ""
        for l in word:
            positional += self.mapping.get(l, '000')
            if last == l:
                sum_image += 2  # words with adjacent repeated letters shouldn't be way apart from each other
            else:
                sum_image += int(self.mapping.get(l, '000'))
            last = l
        return positional, sum_image

    def diff(self, shorter_word, longer_word):
        """Returns a list of the letters that don't exist in both words.
        Args:
            shorter_word (str): The shorter word.
            longer_word (str): The longer word.
        Returns:
            list: A list of the letters that don't exist in both words.

        Example:
            >>> diff("laa", "lab")
            ['a', 'b']
        """
        logging.info("[diff] - Calculating the difference between two words: %s, %s", shorter_word, longer_word)
        diff_list = []
        longer_list=list(longer_word)
        shorter_list=list(shorter_word)
        for i in list(shorter_word):
            if i not in longer_list: diff_list.append(i)
            else:
                longer_list.remove(i)
                shorter_list.remove(i)
        for i in longer_list:
            if i not in shorter_list: diff_list.append(i)

        return diff_list

    def is_h7q9_swap(self, new_word, word):
        """Check if the difference is just a swap of 7-h or 9-q or capital-lower case.
        Args:
            new_word (str): The new word.
            word (str): The word to compare with.
        Returns:
            bool: True if the difference is just a swap of 7-h or 9-q or capital-lower case, False otherwise.

        Example:
            >>> is_h7q9_swap("7amid", "hamid")
            True
        """
        logging.info("[is_h7q9_swap] - Checking if the difference is just a swap of 7-h or 9-q or capital-lower case: %s, %s", new_word, word)
        if (
            new_word.replace("h", "7").replace("q", "9").lower() == word.replace("h", "7").replace("q", "9").lower()
        ):
            return True
        return False

    def _get_longer_and_shorter_word(self, word1, word2):
        """Helper method to determine the longer and shorter of two words."""
        return (word1, word2) if len(word1) > len(word2) else (word2, word1)

    def _calculate_difference_based_distance(self, difference, new_word, word):
        """Calculates distance based on differences in letters."""
        vowels = {"a", "2", "i", "e", "w", "o", "u"}
        if set(difference).issubset(vowels) or self.is_h7q9_swap(new_word, word):
            return 0.1 * len(difference)
        return sum(1 for letter in difference if letter not in vowels)

    def _calculate_edge_letter_penalty(self, longer_word, shorter_word):
        """Calculates penalties based on differences in first and last letters."""
        penalty = 0
        if longer_word[0] != shorter_word[0]:
            penalty += 1
        if longer_word[-1] != shorter_word[-1]:
            penalty += 1
        return penalty

    def _calculate_substring_penalty(self, longer_word, shorter_word):
        """Calculates penalties based on missing substrings."""
        penalty = 0
        interval = 2  # constant for substring length
        for i in range(len(longer_word) - interval + 1):
            substring = longer_word[i:i + interval]
            if substring not in shorter_word:
                penalty += 1
        return penalty

    def distance_between(self, new_word, word):
        """Calculates and returns the distance between two words.
        The distance is calculated based on the difference in letters, the difference in vowels, and the difference in consonants.
        Args:
            new_word (str): The new word.
            word (str): The word to compare with.
        Returns:
            float: The distance between the two words.

        Example:
            >>> distance_between("kelb", "kalb")
            2.1
        """
        logging.info("[distance_between] - Calculating the distance between two words: %s, %s", new_word, word)
        # Check if the words are the same (or if the difference is just a swap of ou and o)
        if new_word.replace("ou", "o") == word.replace("ou", "o"): return 0

        # Get the longer and shorter word, and the difference in letters between them
        longer_word, shorter_word = self._get_longer_and_shorter_word(new_word, word)
        difference = self.diff(shorter_word, longer_word)

        # Calculate the distance based on the difference in letters
        distance = self._calculate_difference_based_distance(difference, new_word, word)
        # Calculate the distance based on the difference in first and last letters
        distance += self._calculate_edge_letter_penalty(longer_word, shorter_word)
        # Calculate the distance based on the difference in substrings
        distance += self._calculate_substring_penalty(longer_word, shorter_word)

        return distance

    def find_numbers_within_threshold(self, number, threshold):
        """Find the closest numbers to a given number in list_of_sum_keys within a threshold (complexity: log(n)).
        Args:
            number (int): The number to compare with.
            threshold (int): The threshold to consider.
        Returns:
            list: A list of the closest numbers within the threshold.

        Example:
            >>> find_numbers_within_threshold(100, 10)
            [90, 91, 94, 95, 96, 100, 102, 103, 104, 109]
        """
        logging.info("[find_numbers_within_threshold] - Finding numbers within threshold: %s, %s", number, threshold)
        left_index = bisect.bisect_left(self.list_of_sum_keys, number - threshold)
        right_index = bisect.bisect_right(self.list_of_sum_keys, number + threshold)
        closest_numbers = self.list_of_sum_keys[left_index:right_index]
        return closest_numbers

    def get_closests(self, word):
        """Get the closest words to a given word.
        Args:
            word (str): The word to compare with.
            sum_threshold (int): The sum threshold to consider.
            distance_threshold (int): The distance threshold to consider.
        Returns:
            tuple: A tuple containing the closest words and the minimum distance.

        Example:
            >>> get_closests("kulb")
            (['klb', 'kelb', 'kalb'], 2.1)
        """
        logging.info("[get_closests] - Getting the closest words to a given word: %s", word)
        _, image = self.get_positional(word)
        list_of_closest = self.find_numbers_within_threshold(image, self.sum_threshold)

        closest_words = []
        for close in list_of_closest:
            items = self.hash_table_sum[close]
            for item in items:
                vocab_word = item['darija']
                d = self.distance_between(word, vocab_word)
                if d < self.distance_threshold:
                    closest_words.append([d, vocab_word])

        if not closest_words:
            return [], False
        sorted_data = sorted(closest_words, key=lambda x: x[0])
        min_distance = sorted_data[0][0]
        top_closets = [item[1] for item in sorted_data[:3]]

        return top_closets, min_distance

    def distance_to_confidence(self, distance, lambda_param=0.5):
        """Transform a distance into a probability of confidence using an exponential decay function.
        Args:
            distance (float): The distance between two words.
            lambda_param (float): The decay rate.
        Returns:
            float: The confidence value.

        Example:
            >>> distance_to_confidence(2.1)
            0.3499377491111553
        """
        confidence = math.exp(-lambda_param * distance)
        return confidence

    def lookup_translation_word(self, word):
        """Get potential translations for a word.
        Args:
            word (str): The word to translate.
        Returns:
            dict: A dictionary containing the potential translations and the confidence.

        Example:
            >>> lookup_translation_word("klb")
            {'potential translations': ['dog', 'he ate', 'eat'], 'confidence': '100%'}
        """
        logging.info("[lookup_translation_word] - Looking up potential translations for word: %s", word)

        # check if the word is a name
        is_name, resp = self.check_name(word)
        if is_name:
            return resp

        # if the word is a not a number, normalize word by replacing 5 with kh and 4 with gh
        if not word.isdigit():
            word = word.replace("5", "kh").replace("4", "gh")

        # get the closest words and the minimum distance
        words, min_distance = self.get_closests(word)
        
        # get all the potential translations of the words
        potential_trans = []
        for w in words:
            potential_trans.append(self.get_all_exact_translations(w))
        potential_trans = list(itertools.chain(*potential_trans))
        if not potential_trans:
            return {}
        # remove duplicates
        unique_list = list(OrderedDict.fromkeys(potential_trans))
        # calculate confidence based on the minimum distance
        confidence = self.distance_to_confidence(min_distance)
        if unique_list == []:
            confidence = 0
        confidence = round(confidence * 100)
        # to avoid returning translations with low confidence, we set a threshold
        # if the confidence is below the threshold, return an empty dictionary
        if confidence < self.acceptance_threshold:
            return {}
        # set max words to return to avoid returning too many words
        # return the potential translations and the confidence.
        response = {
            "potential translations": unique_list[:self.max_words],
            "confidence": f"{confidence}%"
        }

        return response

    def remove_punctuation(self, text):
        """Remove punctuation from text.
        Args:
            text (str): The text to remove punctuation from.
        Returns:
            str: The text without punctuation.
        
        Example:
            >>> remove_punctuation("Salam, afin had lghbour!")
            'Salam afin had lghbour'
        """
        return re.sub(r'[^\w\s]', '', text)

    def check_name(self, word):
        """Check if the word is in the list of names.
        Args:
            word (str): The word to check.
        Returns:
            tuple: A tuple containing a boolean value and a dictionary of potential translations and confidence.
            
        Example:
            >>> check_name("aissam")
            (True, {'potential translations': ['Aissam'], 'confidence': '100%'})
            >>> check_name("tomobil")
            (False, {})
        """
        index = bisect.bisect_left(self.names, word)

        if index < len(self.names) and self.names[index] == word:
            return True, {"potential translations": [word.capitalize()], "confidence": "100%"}
        else:
            return False, {}

    def get_all_exact_translations(self, word):
        """Get all the exact translations of a word.
        Args:
            word (str): The word to get the exact translations of.
        Returns:
            list: A list of the exact translations of the word.

        Example:
            >>> get_all_exact_translations("klb")
            ['dog']
        """
        results = []
        for i in self.exact:
            if i[0] == word:
                results.append(i[1])
        return results
