import os
import pickle
import csv

class DataLoader:
    def __init__(self, base_dir):
        self.base_dir = base_dir

    def load_pickle(self, filename):
        """Load a pickle file."""
        try:
            with open(os.path.join(self.base_dir, 'data', filename), 'rb') as handle:
                return pickle.load(handle)
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{filename}' was not found. Please ensure it exists in the 'data' directory.")
        except pickle.UnpicklingError:
            raise ValueError(f"The file '{filename}' is not a valid pickle file or is corrupted.")

    def load_translations(self, filename='translations.csv'):
        """Load the exact translations from a CSV file."""
        try:
            with open(os.path.join(self.base_dir, 'data', filename), newline='') as f:
                reader = csv.reader(f)
                translation_data = [row for row in reader]
            translation_data.remove(['darija', 'english'])
            return translation_data
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{filename}' was not found. Please ensure it exists in the 'data' directory.")
        except ValueError as e:
            raise ValueError(f"Error reading '{filename}': {e}")

    def load_names(self, filename='names.csv'):
        """Load the list of names from a CSV file."""
        try:
            with open(os.path.join(self.base_dir, 'data', filename), newline='') as f:
                reader = csv.reader(f)
                names = [row[0] for row in reader]
            names.remove("names")
            names = sorted(names)
            return names
        except FileNotFoundError:
            raise FileNotFoundError(f"The file '{filename}' was not found. Please ensure it exists in the 'data' directory.")
        except ValueError as e:
            raise ValueError(f"Error reading '{filename}': {e}")