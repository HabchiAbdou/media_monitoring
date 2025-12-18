class Mappings:
    def __init__(self):
        self.mapping_vowels = {
            "a": '003', "2": '001', 'i': '004', "e": '002', "w": '005', "o": '006', "u": '007', "y": "10"
        }
        self.mapping_consonants = {
            "l": '40', "f": '50', "t": '60', "T": '65', "b": '75',
            "3": '700', "p": '735',
            "D": '750', "d": '755', "g": '800', "j": '810', "m": '820',
            "n": '830', "r": '840', "v": '850', "8": '873', "h": '880', "7": '887',
            "S": '900', "s": '905', "c": '910', "k": '915',
            "q": '920', "9": '930', "x": '980', "z": '999'
        }
        self.mapping = {}
        self.mapping.update(self.mapping_vowels)
        self.mapping.update(self.mapping_consonants)

    def get_mapping(self):
        return self.mapping
