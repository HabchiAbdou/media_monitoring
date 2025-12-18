import os
import csv
import pickle
from DarijaDistance.mappings import Mappings
import logging

logging.basicConfig(level=logging.WARNING)

class DarijaEncoder:
    def __init__(self, mappings):
        self.mapping = mappings.get_mapping()
        self.hash_table_word = {}
        self.hash_table_sum = {}
        self.list_of_sum_keys = []

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
        if not isinstance(word, str): 
            return word
        
        positional = ""
        sum_image = 0
        last = ""
        for l in word:
            positional += self.mapping.get(l, '000')
            sum_image += 2 if last == l else int(self.mapping.get(l, '000'))
            last = l
        
        return positional, sum_image

    def load_csv(self, exact_path):
        """
        Loads data from a CSV file and populates hash tables.

        This method reads the content of the specified CSV file and uses it to populate the hash tables for words and their positional and sum encodings.

        Args:
            exact_path (str): The path to the CSV file to load.
        """
        with open(exact_path, newline='') as f:
            reader = csv.reader(f)
            exact = [row for row in reader]
        exact.remove(['darija', 'english'])
        
        self.populate_hash_tables(exact)
    
    def populate_hash_tables(self, exact_data):
        """
        Populates the hash tables based on the exact data provided.

        This method iterates through the provided data and generates positional and sum encodings for each word. It then stores these encodings in hash tables.

        Args:
            exact_data (list): A list of tuples containing words and their translations.
        """
        for key, value in exact_data:
            if key not in self.hash_table_word:
                self.hash_table_word[key] = []
            v = {
                "translation": value,
                "positional_encoding": self.get_positional(key)[0],
                "sum_encoding": self.get_positional(key)[1],
            }
            self.hash_table_word[key].append(v)

        for key, value in self.hash_table_word.items():
            for i in range(len(value)):
                sum_encoding = value[i]['sum_encoding']
                if sum_encoding not in self.hash_table_sum:
                    self.hash_table_sum[sum_encoding] = []
                self.hash_table_sum[sum_encoding].append({
                    "darija": key,
                    "translation": value[i]["translation"],
                    "positional_encoding": value[i]["positional_encoding"],
                })

        self.list_of_sum_keys = sorted(self.hash_table_sum.keys())

    def save_to_pickle(self, word_path, sum_path, keys_path):
        """
        Saves hash tables and the list of sum keys to pickle files.

        This method serializes the hash tables and the list of sum keys to the specified file paths using pickle.

        Args:
            word_path (str): The file path to save the word hash table.
            sum_path (str): The file path to save the sum hash table.
            keys_path (str): The file path to save the list of sum keys.
        """
        with open(word_path, 'wb') as handle:
            pickle.dump(self.hash_table_word, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(sum_path, 'wb') as handle:
            pickle.dump(self.hash_table_sum, handle, protocol=pickle.HIGHEST_PROTOCOL)
        with open(keys_path, 'wb') as handle:
            pickle.dump(self.list_of_sum_keys, handle, protocol=pickle.HIGHEST_PROTOCOL)


class DarijaDataManager:
    def __init__(self):
        self.encoder = DarijaEncoder(Mappings())

    def add_name(self, name, names_csv_path=None):
        """
        Adds a new name to the names.csv file and sorts the file alphabetically.

        This method checks if the specified name already exists in the CSV file. If the name does not exist, it adds the name, sorts the list alphabetically, and writes it back to the file.

        Args:
            name (str): The name to be added.
            names_csv_path (str, optional): The path to the names.csv file. Defaults to './DarijaDistance/data/names.csv'.
        """
        # Determine the correct path if not provided
        if not names_csv_path:
            names_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'names.csv')
        
        if not names_csv_path:
            raise ValueError("The path to the names.csv file is not provided or invalid.")
        
        # Initialize the list of names
        names = []

        # Check if the file exists and read existing names
        if os.path.exists(names_csv_path):
            with open(names_csv_path, newline='') as f:
                reader = csv.reader(f)
                # Skip the header
                next(reader, None)
                names = [row[0] for row in reader if row]

        # Add new name and sort if not already in the list
        if name not in names:
            names.append(name)
            names = sorted(names)
        else:
            logging.error(f"Name '{name}' already exists in the list of names.")
            return

        # Write sorted names back to the file
        with open(names_csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['names'])  # Write header
            for n in names:
                writer.writerow([n])
    
    def add_translations(self, translations, translations_csv_path=None):
        """
        Adds new words and their translations to the translations.csv file with validation.

        This method checks if the translations already exist in the CSV file. If they do not exist, it appends the new translations and regenerates the hash tables and pickle files.

        Args:
            translations (list): A list of tuples containing words and their translations, in that order. 
            translations_csv_path (str, optional): The path to the translations.csv file. Defaults to './DarijaDistance/data/translations.csv'.
        
        Raises:
            ValueError: If any of the translations are not a tuple of two elements.

        Example:
            >>> add_translations([("la", "no"), ("klb", "dog")])
        """
        # Validate each translation entry
        for translation in translations:
            if not isinstance(translation, (list, tuple)) or len(translation) != 2:
                raise ValueError(f"Invalid translation entry: {translation}. Expected a list or tuple with two elements.")

        if not translations_csv_path:
            translations_csv_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'translations.csv')

        existing_translations = set()

        # Check if the file exists and read existing translations
        if os.path.exists(translations_csv_path):
            with open(translations_csv_path, newline='') as f:
                reader = csv.reader(f)
                existing_translations = set(tuple(row) for row in reader)

        # Filter out the translations that already exist
        new_translations = [tuple(t) for t in translations if tuple(t) not in existing_translations]

        if not new_translations:
            logging.error("All translations already exist in the translations CSV file.")
            return

        try:
            with open(translations_csv_path, 'a', newline='') as f:
                writer = csv.writer(f)
                for translation in new_translations:
                    writer.writerow(translation)
            
            # Re-generate hash tables and pickle files
            self.encoder.load_csv(translations_csv_path)
            self.encoder.save_to_pickle(
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'hash_table_word.pickle'), 
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'hash_table_sum.pickle'),
                os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data', 'list_of_sum_keys.pickle')
            )
        
        except (IOError, OSError) as e:
            print(f"Error writing to the translations CSV file or generating pickle files: {e}")
            raise
