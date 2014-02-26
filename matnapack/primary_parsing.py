import os
import sys
import re
import stat


is_comment = re.compile(r'^\s*\%', re.M)
_is_mex_or_m_file = re.compile(r'\S*\.(m|mex)[^\.]*$', re.M)


def is_mex_or_m_file(filename):
    '''
    >>> is_mex_or_m_file('foo.mexw64')
    True
    >>> is_mex_or_m_file('foo/bar.mexw64')
    True
    '''
    return bool(_is_mex_or_m_file.match(filename))


def get_mex_files(matlab_files, mfilename):
    return [filename for filename in matlab_files \
            if filename.startswith('.mex')]


def is_m_file(filename):
    return bool(filename.endswith('.m'))


def has_a_comment(line):
    return bool(is_comment.search(line))


def fix_permissions(filename):
    fstat = os.stat(filename)
    mode = fstat.st_mode | stat.S_IWUSR
    os.chmod(filename, mode)


def remove_comments(filename):
    print('Removing comments from %s' % filename)
    input_handle = open(filename)
    lines = [line for line in input_handle]
    cleaned = list()
    for line in lines:
        if has_a_comment(line):
            continue
        cleaned.append(line.rstrip())
    output_handle = open(filename, 'w+')
    output_handle.write('\n'.join(cleaned))
    output_handle.close()
