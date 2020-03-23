from .calculator import Calculator
from .readability import Readability
from .dependency_distance import DepDistance
from .macroetym.etym import Etym
from .call_by_language import call_by_language
import pandas as pd

class TextDescriptives():
    def __init__(self, texts, lang = 'da', category = 'all', measures = 'all', stanza_path = None, globalize_stanza = True):
        """
        texts: str/list/pd.Series containing text
        lang: str/list with the language code(s)
        category: which categories to calculate. Options are ['all', 'basic', 'readability', 'etymology', 'dep_distance']
        measures: if you only want to calculate specific measures (don't use atm)
        globalize_stanza (bool): whether to make the stanza pipeline global to avoid reloading on multiple calls.
          Only uses global pipeline if settings (language, stanza_path and processors) match.
        """

        self.lang = lang
        self.stanza_path = stanza_path
        self.globalize_stanza = globalize_stanza

        if isinstance(lang, list):
            self.df = call_by_language(
                clss = TextDescriptives,
                texts = texts, 
                langs = lang, 
                category = category, 
                measures = measures, 
                stanza_path = stanza_path,
                globalize_stanza = globalize_stanza)
        else:
            if not isinstance(texts, (str, list, pd.Series)):
                raise TypeError(f"'texts' should be string, list, or pandas.Series, not {type(texts)}.")

            # """ TODO Consider adding token dfs
            # token_dfs: list of pd.DataFrame objects. (optional)
            #   Each data frame must contain these columns:
            #     "sentence_id" : The index of the sentence in the text.
            #     "token_position" : The position of the token in the sentence.
            #     "token" : The token.
            #     "pos" : The POS tag of the token.
            #     "governor": The governor from dependency parsing. (Only required when running 'dep_distance' category).
            #     "dep_rel": Dependency relation from dependency parsing. (Only required when running 'dep_distance' category).
            # """
            # if token_dfs is not None:
            #     if not isinstance(token_dfs, list): 
            #         raise TypeError(f"'token_dfs' should be list of pandas.DataFrame objects, not {type(token_dfs)}.")
            #     if not isinstance(token_dfs[0], pd.DataFrame):
            #         raise TypeError(f"'token_dfs' should be list of pandas.DataFrame objects, not list of {type(token_dfs[0])}.")

            if isinstance(texts, str):
                texts = [texts]
            self.df = pd.DataFrame(texts, columns = ['Text'])
            # self.token_dfs = token_dfs
            
            # Category check
            valid_categories = set(['all', 'basic', 'readability', 'entropy', 'sentiment', 'etymology', 'dep_distance'])

            if not isinstance(category, (str, list)):
                raise TypeError(f"'category' should be string or list of strings, not {type(category)}")
            if isinstance(category, str):
                category = [category]
            if not set(category).issubset(valid_categories):
                raise ValueError(f"'category' contained invalid category.\nValid categories are: ['all', 'basic', 'readability', 'etymology', 'dep_distance']")
            
            if 'all' in category:
                self.__basic()
                self.__readability()
                self.__etymology()
                self.__dependency_distance()
            else:
                if 'basic' in category:
                    self.__basic(measures = measures)
                if 'readability' in category:
                    self.__readability(measures = measures)
                if 'etymology' in category:
                    self.__etymology()
                if 'dep_distance' in category:
                    self.__dependency_distance()

    def __basic(self, measures = 'all'):
        """
        Calculates simple descriptive statistics
        """
        basic_calc = Calculator(lang = self.lang)
        calculated_metrics = basic_calc.calculate_metrics(texts = self.df['Text'], metrics = measures)
        self.df = pd.concat([self.df, calculated_metrics], axis = 1)

    def __readability(self, measures = 'all'):
        """
        Calculates readability scores
        """
        read = Readability(lang = self.lang)
        calculated_metrics = read.calculate_metrics(texts = self.df['Text'], metrics = measures)
        self.df = pd.concat([self.df, calculated_metrics], axis = 1)

    def __etymology(self, remove_empty = True):
        """
        Calculates emymological origins of the text using the macroetym package
        Further calculates ratio of words with Germanic to Latinate origins
        """
        from iso639 import languages

        # Macroetym uses 3 letter language codes, have to map them to iso-639
        lan = languages.get(part1 = self.lang).part3

        etym_df = Etym(self.df['Text'], lang = lan).T
        etym_df = etym_df.reset_index().rename({'index' : 'Text'}, axis = 1)
        
        self.etym_df = etym_df

        self.df = pd.merge(self.df, etym_df, on ='Text')
        try:
            self.df['Latinate/Germanic'] = self.df['Latinate'] / self.df['Germanic']
        except KeyError:
            self.df['Latinate/Germanic'] = 'No Latinate'
        
    def __dependency_distance(self):
        """
        Calculates mean dependency distance (MDD) of each text, following http://www.lingviko.net/jcs.pdf
        Dependency distance (DD) = abs(governor - dependent)
        As such, adjacent words have a DD of 1. Roots are defined as have a DD of 0
        MDD is calculated on sentence level, ie. MDD is the mean of the average dependency distance pr sentence.
        Mean and standard deviation of the proportion of adjacent dependency relations pr sentence is further calculated
        """
        dep = DepDistance(text = self.df['Text'], lang = self.lang, 
                          stanza_path = self.stanza_path, 
                          globalize_stanza = self.globalize_stanza)
        self.df = pd.concat([self.df, dep.get_text_distances()], axis = 1)
    
    def __entropy(self):
        pass

    def __sentiment(self):
        pass

    def get_df(self):
        return self.df


def all_metrics(texts, lang = 'en', stanza_path = None, globalize_stanza = False):
    """
    Calculates all implemented statistical metrics
    text: str/list/pd.Series of strings
    lang: two character language code, e.g. 'en', 'da'
    stanza_path: string, path to stanza resources
    globalize_stanza (bool): whether to make the stanza pipeline global to avoid reloading on multiple calls.
      Only uses global pipeline if settings (language, stanza_path and processors) match.
    """
    return TextDescriptives(texts, lang = lang, category = 'all', 
                            stanza_path = stanza_path, 
                            globalize_stanza = globalize_stanza).df

def basic_stats(texts, lang = 'en', metrics = 'all'):
    """
    Calculates standard descriptive statistics
    text: str/list/pd.Series of strings
    lang: string, two character language code
    measures: string/list of strings, which measures to calculate
    """
    return TextDescriptives(texts, lang = lang, category = 'basic', measures = metrics).df

def readability(texts, lang = 'en', metrics = 'all'):
    """
    Calculates readability metrics
    texts: str/list/pd.Series of strings
    lang: string, two character language code
    measures: string/list of strings, which measures to calculate
    """
    return TextDescriptives(texts, lang = lang, category = 'readability', measures = metrics).df

def etymology(texts, lang = 'en'):
    """
    Calculates measures related to etymology
    texts: str/list/pd.Series of strings
    lang: string, two character language code
    """
    return TextDescriptives(texts, lang = lang, category = 'etymology').df

def dependency_distance(texts, lang = 'en', stanza_path = None, globalize_stanza = False):
    """
    Calculates measures related to etymology
    texts: str/list/pd.Series of strings
    lang: string, two character language code
    stanza_path: string, path to stanza resources
    globalize_stanza (bool): whether to make the stanza pipeline global to avoid reloading on multiple calls.
      Only uses global pipeline if settings (language, stanza_path and processors) match.
    """
    return TextDescriptives(texts, lang = lang, 
                            category = 'dep_distance', 
                            stanza_path = stanza_path, 
                            globalize_stanza = globalize_stanza).df