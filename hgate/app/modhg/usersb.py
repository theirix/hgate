import random
import crypt
import os
import repository
import settings
from app.modhg.HGWeb import HGWeb

__author__ = 'Shedar'

def list(filename):
    lines = _get_rows(filename)
    login_list = []
    for line in lines:
        login, hash = line.split(':')
        login_list.append(login)
    login_list.sort()
    return login_list

def exists(filename,login):
    lines = _get_rows(filename)
    match = [line for line in lines if line.startswith(login)]
    if match:
        return True
    return False


def add(filename,login,password):
    lines = _get_rows(filename)
    match = [line for line in lines if line.startswith(login)]
    if match:
        raise ValueError("User exists")
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

def permissions(filename, login):
    #check is login exists
    permission_list = {}
    hgweb = HGWeb(settings.HGWEB_CONFIG) # todo: refactor to remove settings usage here
    paths = hgweb.get_paths()
    for (name, path) in paths:
        if path.endswith("*"):
            permission_list.update(_scan(name, path, path.endswith("**"), login))
        else:
            if repository.is_repository(path):
                perm = _extract_permission(login, path)
                if perm:
                    permission_list[name.strip(os.sep)] = perm
    return  permission_list

def _scan(name, dir, deep, login):
    permission_list = {}
    dir = dir.rstrip("*")
    if not os.path.exists(dir):
        return permission_list
    dir_list = os.listdir(dir)
    for current_dir in dir_list:
        path = os.path.join(dir, current_dir)
        if repository.is_repository(path):
            perm = _extract_permission(login, path)
            if perm:
                permission_list[os.path.join(name, current_dir)] = perm
        elif deep:
            permission_list.update(_scan(os.path.join(name, current_dir), path, deep, login))
    return permission_list

def _extract_permission(login, path):
    hgrc_path = os.path.join(path,".hg","hgrc")
    if not os.path.exists(hgrc_path):
        return False
    hgrc = HGWeb(hgrc_path) #todo: replace with local config class
    web = hgrc.get_web()
    allow_read = not _is_in_list(web, "deny_read", login) and \
                 _is_in_list(web, "allow_read", login)
    allow_push = not _is_in_list(web, "deny_push", login) and \
                 _is_in_list(web, "allow_push", login)
    if allow_read or allow_push:
        return {"read": allow_read, "push": allow_push}
    return False

def _is_in_list(web, key, login):
    res = [value for (name, value) in web if name==key]
    if len(res) > 0:
        value = res[0]
        if value.find("*")>=0:
            return True
        else:
            raw_login_list = value.split(",")
            login_list = [ item.strip() for item in raw_login_list]
            try:
                login_list.index(login)
                return True
            except ValueError:
                return False

def _salt():
    letters = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/.'
    return random.choice(letters) + random.choice(letters)

def _form_file_row(login, password):
    return login + ":" + crypt.crypt(password, _salt()) + os.linesep

def _get_rows(filename):
    lines = open(filename, 'r').readlines()
    return [line.strip("\r\n") + os.linesep for line in lines]
