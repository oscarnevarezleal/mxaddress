#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import string
import warnings
from collections import OrderedDict

import pycrfsuite

#  _____________________
# |1. CONFIGURE LABELS! |
# |_____________________|
#     (\__/) ||
#     (•ㅅ•) ||
#     / 　 づ
LABELS = [
    'AddressNumberPrefix',
    'AddressNumber',
    'AddressNumberUndefined',
    'AddressNumberSuffix',
    'StreetNamePreModifier',
    'StreetNamePreDirectional',
    'StreetNamePreType',
    'StreetName',
    'StreetNamePostType',
    'StreetNamePostDirectional',
    'SubaddressType',
    'SubaddressIdentifier',
    'DistrictSuffix',
    'District',
    'DistrictUndefined',
    'DistrictType',
    'BuildingName',
    'OccupancyType',
    'OccupancyIdentifier',
    'CornerOf',
    'LandmarkName',
    'PlaceName',
    'StateName',
    'ZipCodePrefix',
    'ZipCode',
    'USPSBoxType',
    'USPSBoxID',
    'USPSBoxGroupType',
    'USPSBoxGroupID',
    'IntersectionHintStart',
    'IntersectionSeparator',
    'Recipient',
    'NotAddress',
    'CityPrefix',
    'City',
    'State'
]  # The labels should be a list of strings

STREET_NAMES = {
    'calle', 'avenida', 'av', 'ave', 'blvd', 'avenida', 'cerrada', 'privada', 'priv', 'circuito', 'cto',
    'prolng', 'ret', 'fcc'
}

SUBADDRESS_TYPES = {
    'MZA', 'MZ', 'LT', 'LOTE', 'INT'
}

DISTRICT_TYPES = {
    'col', 'colonia', 'fracc.', 'fraccionamiento'
}
INTERSECTIONS_INDICATORS = {
    'entre'
}
INTERSECTIONS = {
    '&', 'y', 'esquina con', 'esq.con', 'esq', 'casi'
}

CITY_PREFIXES = {
    'mpo.', 'deleg.'
}

ARTICLES = {
    'la', 'las', 'el', 'los', 'un', 'uno', 'una', 'unas'
}

CONTRACTIONS = {
    'de', 'del', 'al', 'por', 'para'
}

LEGACY_AND_NEW_DF = {
    'distrito federal'
    , 'ciudad de mexico'
    , 'ciudad de méxico'
    , 'ciudad de m\xc3\x89XICO'
    , 'CIUDAD DE MEXICO'
    , 'cdmx'
}

# ***************** OPTIONAL CONFIG ***************************************************
PARENT_LABEL = 'OrderCollection'  # the XML tag for each labeled string
GROUP_LABEL = 'OrderString'  # the XML tag for a group of strings
NULL_LABEL = 'Null'  # the null XML tag
MODEL_FILE = 'learned_settings.crfsuite'  # filename for the crfsuite settings file
# ************************************************************************************


try:
    TAGGER = pycrfsuite.Tagger()
    TAGGER.open(os.path.split(os.path.abspath(__file__))[0] + '/' + MODEL_FILE)
except IOError:
    TAGGER = None
    warnings.warn(
        'You must train the model (parserator train [traindata] [modulename]) to create the {} file before you can '
        'use the parse and tag methods'.format(
            MODEL_FILE))


def parse(raw_string):
    if not TAGGER:
        raise IOError(
            '\nMISSING MODEL FILE: {}\nYou must train the model before you can use the parse and tag methods\nTo '
            'train the model annd create the model file, run:\nparserator train [traindata] [modulename]'.format(
                MODEL_FILE))

    tokens = tokenize(raw_string)
    if not tokens:
        return []

    features = tokens2features(tokens)

    tags = TAGGER.tag(features)
    d = list(zip(tokens, tags))
    return d


def tag(raw_string):
    # remove hidden characters
    raw_string = ''.join([x for x in raw_string if ord(x) < 128])
    # convert to utf8
    raw_string = raw_string.encode('utf-8')
    tagged = OrderedDict()
    prev_label = None
    is_occupancy = False
    is_occupancy_ending = False
    is_intersection = False
    is_intersection_ending = False

    # Check for CDMX list in raw_String
    df_list = list(LEGACY_AND_NEW_DF)
    for e in df_list:
        if raw_string.lower().find(e) > -1:
            # Add tag
            tagged.setdefault("cdmx", []).append("1")
            break

    for token, label in parse(raw_string):
        # not interested in empty tokens
        # print (label, token)

        if token == ' ':
            continue

        if label == 'IntersectionHintStart':
            is_intersection = True

        if label == 'IntersectionSeparator':
            is_intersection_ending = True

        if label == 'OccupancyType':
            # are we already been here?
            if is_occupancy:
                label = "Second" + label
                is_occupancy_ending = True
            is_occupancy = True

        if 'OccupancyIdentifier' in label and is_occupancy:
            if is_occupancy_ending:
                label = "Third" + label
            else:
                label = "Second" + label

        if 'StreetName' in label and is_intersection:
            if is_intersection_ending:
                label = "Third" + label
            else:
                label = "Second" + label
                # @todo
                # tagged.setdefault("CornerOf", []).append(token)

        # avoid duplicated information
        if label in tagged:
            if tagged[label][0].find(token.strip(' ,;')) > -1:
                continue

        if label == prev_label:
            print "Label sequence detected with" + label + ", " + token
            tagged[label][0] += " " + token
        else:
            tagged.setdefault(label, []).append(token)

        prev_label = label
        # prev_token = token

    for token in tagged:
        component = ' '.join(tagged[token])
        component_stripped = component.strip(' ,;')
        tagged[token] = component_stripped

    # print tagged
    return tagged


#  _____________________
# |2. CONFIGURE TOKENS! |
# |_____________________|
#     (\__/) ||
#     (•ㅅ•) ||
#     / 　 づ
def tokenize(raw_string):
    # this determines how any given string is split into its tokens
    # handle any punctuation you want to split on, as well as any punctuation to capture

    if isinstance(raw_string, bytes):
        try:
            raw_string = str(raw_string, encoding='utf-8')
        except:
            raw_string = str(raw_string)

    re_tokens = re.compile(r'''
                               \(*\b[^\s,;#&()]+[.,;)\n]*|[#&]
                               ''', re.VERBOSE | re.UNICODE)

    tokens = re_tokens.findall(raw_string)

    print("raw_string=" + raw_string)
    print("tokens=")
    print(tokens)

    if not tokens:
        return []
    return tokens


#  _______________________
# |3. CONFIGURE FEATURES! |
# |_______________________|
#     (\__/) ||
#     (•ㅅ•) ||
#     / 　 づ
def tokens2features(tokens):
    # this should call tokenFeatures to get features for individual tokens,
    # as well as define any features that are dependent upon tokens before/after

    feature_sequence = [tokenFeatures(tokens[0])]
    previous_features = feature_sequence[-1].copy()

    # print(tokens)
    # print(feature_sequence)
    # print (tokens[0], previous_features)

    for token in tokens[1:]:
        # set features for individual tokens (calling tokenFeatures)
        token_features = tokenFeatures(token)
        current_features = token_features.copy()

        # print(token)
        # print(token_features)

        # features for the features of adjacent tokens
        feature_sequence[-1]['next'] = current_features
        token_features['previous'] = previous_features

        # DEFINE ANY OTHER FEATURES THAT ARE DEPENDENT UPON TOKENS BEFORE/AFTER
        # for example, a feature for whether a certain character has appeared previously in the token sequence

        feature_sequence.append(token_features)
        previous_features = current_features

    feature_sequence[0]['address.start'] = True
    feature_sequence[-1]['address.end'] = True

    if len(feature_sequence) > 1:
        # these are features for the tokens at the beginning and end of a string
        feature_sequence[0]['rawstring.start'] = True
        feature_sequence[-1]['rawstring.end'] = True
        feature_sequence[1]['previous']['rawstring.start'] = True
        feature_sequence[-2]['next']['rawstring.end'] = True

    else:
        # a singleton feature, for if there is only one token in a string
        feature_sequence[0]['singleton'] = True

    return feature_sequence


def tokenFeatures(token):
    # token_clean = re.sub(r'(^[\W]*)|([^.\w]*$)', '', token, re.UNICODE)
    # token_abbrev = re.sub(r'[.]', u'', token_clean.lower())

    if token == '' or token is None:
        return {}

    features = {  # DEFINE FEATURES HERE. some examples:
        'length': len(token),
        'case': casing(token),
        'digits': digits(token),
        'contraction': token.lower() in CONTRACTIONS,
        'article': token.lower() in ARTICLES,
        'street_abbrev': token in STREET_NAMES,
        'sub_address': token in SUBADDRESS_TYPES,
        'intersection_indication': token in INTERSECTIONS_INDICATORS,
        'intersection': token in INTERSECTIONS,
        'city_prefix': token.lower() in CITY_PREFIXES
    }

    return features


def digits(token):
    if token.isdigit():
        return 'all_digits'
    elif set(token) & set(string.digits):
        return 'some_digits'
    else:
        return 'no_digits'


# define any other methods for features. this is an example to get the casing of a token
def casing(token):
    if token.isupper():
        return 'upper'
    elif token.islower():
        return 'lower'
    elif token.istitle():
        return 'title'
    elif token.isalpha():
        return 'mixed'
    else:
        return False
