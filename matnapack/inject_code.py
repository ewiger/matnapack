from __future__ import print_function
import os
import re
import sys
import argparse
import signal
from .primary_parsing import (is_m_file, has_a_comment)
from pyparsing import Word, alphanums, delimitedList, Keyword, Optional, Literal

from pprint import pprint


DRY_RUN = False

# Grammar
ID = alphanums + '_'
out_vars = '[' + delimitedList(Word(ID)).setResultsName('out_vars') + ']'
in_vars = '(' + delimitedList(Word(ID)).setResultsName('in_vars') + ')'


#E.g. function[s,val,posdef,count,lambda]=trust(g,H,delta)
function_grammar1 = 'function' + out_vars + Literal('=') \
                    + Word(ID).setResultsName('fname') + in_vars
function_grammar2 = 'function' + Optional( Word(ID) + '=' ) \
                    + Word(ID).setResultsName('fname') + '()'
function_grammar3 = 'function' + Optional(out_vars + '=') \
                    + Word(ID).setResultsName('fname') + Optional(in_vars)


class FuncDeclarationSplitter(object):

    def __init__(self, text):
        # Remove <...> separations.
        self.text = REPL_DOTS_EXPR.sub('', text)
        self.grammar = (function_grammar1, function_grammar2, function_grammar3)

    def parseFunction(self, line):
        if not 'function' in line or has_a_comment(line):
            return None
        # if DRY_RUN:
        #     print(line)
        result = None
        for thing in self.grammar:
            result = list(thing.scanString(line))
            if len(result) > 0:
                break
        return result

    def strip_whitespaces(self, line):
        return line.replace('\t', '')\
                   .replace(' ', '')\
                   .strip()

    def declares_function(self, line):
        result = self.parseFunction(line)
        if not result or not re.match('^function', line):
            return False
        # if DRY_RUN:
        #   print(result)
        return True

    def split(self):
        result = ['']
        lines = self.text.split('\n')
        for line in lines:
            if has_a_comment(line):
                continue
            first_line_wo_comment = self.strip_whitespaces(line)
            break
        if not self.declares_function(self.strip_whitespaces(first_line_wo_comment)):
            print('First line w/o comment does not declare a function! \n"%s"' %
                  first_line_wo_comment)
            return result
        body = ''
        for line in lines:
            stripped_line = self.strip_whitespaces(line)
            if self.declares_function(stripped_line):
                print('Found declaration: ' + line)
                if body:
                    result.append(body)
                result.append(line)
                body = ''
            else:
                body += line + '\n'
        if body:
            result.append(body)
        if len(result) > 1:
            # Imitate re.split
            result += ['']
        return result


# Injection

VALID_FUNC_EXPR = re.compile(r'^\s*function\s+[^\)]*\)$')

REPL_DOTS_EXPR = re.compile(r'\.\.\.\s*\r?\n?')
REPL_DOTS_EXPR_SIMPLE = re.compile(r'\.\.\.\r?\n')


def hide_dots(text, simple=True):
    if simple:
        return REPL_DOTS_EXPR_SIMPLE.sub('', text)

    result = ''
    lines = [line for line in text.split('\n')
             if not has_a_comment(line)]

    for line in lines:
        (new_line, number_of_subs_made) = REPL_DOTS_EXPR.subn(' ', line)
        if number_of_subs_made == 0:
            result += line + '\n'
            continue
        result += line
    result = result.split('\n')
    result = '\n'.join([result[0], '% compiled'] + result[1:])
    return result


def inject_into_parsed_function(header, body, statement):
    return '\n'.join([header.rstrip(), statement, body])


def parse_functions(text):
    # Remove <...> separations.
    text = hide_dots(text)
    # Split into header and body.
    #sections = FUNCTION_HEADER_EXPR.split(text)
    sections = FuncDeclarationSplitter(text).split()
    #print(len(sections))
    if len(sections) == 1:
        # No split means no match.
        return None
    if len(sections[0]) == 0:
        sections = sections[1:]
    if len(sections[-1]) == 0:
        sections = sections[:-1]
    declarations = list()
    for index, section in enumerate(sections):
        if index % 2 == 0:
            entry = dict()
            entry['header'] = section.rstrip()
        else:
            entry['body'] = section.lstrip()
            declarations.append(entry)
    return declarations


def split_into_sections(text):
    valid_functions = list()
    declarations = parse_functions(text)
    if DRY_RUN:
        print(declarations)
    if not declarations:
        return []
    last_valid_header = ''
    body = ''
    for declaration in declarations:
        header = declaration['header']
        if VALID_FUNC_EXPR.match(header):
            # OK its a valid function, but we also have to check the body
            if len(body) > 0 and len(last_valid_header) > 0:
                # but there is already another one before it
                valid_functions.append({'body': body, 'header': last_valid_header})
                last_valid_header = ''
                body = declaration['body']
            # Do not append will be appended at the end when the body is
            # complete.
            last_valid_header = header
            continue
        # No, it is not a valid function. Correcting a splitting mistake.
        body += declaration['header'] + declaration['body']
    # Finally, check if there is a hanging tail-function with a body.
    if len(body) > 0 and len(last_valid_header) > 0:
        # there is => append it
        valid_functions.append({'body': body, 'header': header})
    return valid_functions


def inject_stmt_into_function(file_path, statement):
    text = file(file_path).read()
    #functions = split_into_sections(text)
    functions = parse_functions(text)
    if not functions:
        print('No function was found in %s. Skipping..' % file_path)
        return False
    if not all(len(declaration) == 2 for declaration in functions):
        raise Exception('Error! Unbalanced parsing results in declarations')
    new_text = ''
    for declaration in functions:
        if statement in declaration['body']:
            print('CMT statement was already injected. Trying to parse next')
            continue
        new_text += inject_into_parsed_function(
            declaration['header'], declaration['body'], statement)
    if len(new_text) > 0:
        # Use opportunity to get rid of nasty \r
        new_text  = new_text.replace('\r', '')
        if DRY_RUN:
            print('Will overwrite %s with:' % file_path)
            print(new_text)
        else:
            with file(file_path, 'w+') as output:
                output.write(new_text)
    return True


def inject_stmt_into_class(file_path, statement):
    return False


def inject_stmt(file_path, statement):
    if not inject_stmt_into_function(file_path, statement):
        # Not a function. Check if it is a class?
        return inject_stmt_into_class(file_path, statement)
    return False
