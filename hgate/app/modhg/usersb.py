import random
import crypt
import os

__author__ = 'Shedar'

def list(filename):
    lines = _get_rows(filename)
    login_list = []
    for line in lines:
        login, hash = line.split(':')
        login_list.append(login)
    return login_list

def add(filename,login,password):
    lines = _get_rows(filename)
    match = [line for line in lines if line.startswith(login)]
    if match:
        raise ValueError("User already exists")
    row = _form_file_row(login, password)
    lines.append(row)
    open(filename,'w+').writelines(lines)

def remove(filename, login):
    # todo: check is user exists in hgrc files
    lines = open(filename, 'r').readlines()
    matches = [line for line in lines if not line.startswith(login)]
    open(filename,'w+').writelines(matches)

def update(filename, login, new_password):
    lines = _get_rows(filename)
    match = [line for line in lines if line.startswith(login)]
    if not match:
        raise ValueError("User not found")
    matches = [line for line in lines if not line.startswith(login)]
    row = _form_file_row(login, new_password)
    matches.append(row)
    open(filename,'w+').writelines(matches)

def _salt():
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.'
    return random.choice(letters) + random.choice(letters)

def _form_file_row(login, password):
    return login + ":" + crypt.crypt(password, _salt()) + os.linesep

def _get_rows(filename):
    lines = open(filename, 'r').readlines()
    return [line.strip("\r\n") + os.linesep for line in lines]
