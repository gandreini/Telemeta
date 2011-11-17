#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010 Guillaume Pellerin
# All rights reserved.
#
# This software is licensed as described in the file COPYING, which
# you should have received as part of this distribution. The terms
# are also available at http://svn.parisson.org/telemeta/TelemetaLicense.
#
# Author: Guillaume Pellerin <yomguy@parisson.com>
#

import os
import sys
import csv
import logging
import datetime
from django.core.management import setup_environ
from django.core.files.base import ContentFile


class Logger:

    def __init__(self, file):
        self.logger = logging.getLogger('myapp')
        self.hdlr = logging.FileHandler(file)
        self.formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        self.hdlr.setFormatter(self.formatter)
        self.logger.addHandler(self.hdlr)
        self.logger.setLevel(logging.INFO)

    def info(self, prefix, message):
        self.logger.info(' ' + prefix + ' : ' + message.decode('utf8'))

    def error(self, prefix, message):
        self.logger.error(prefix + ' : ' + message.decode('utf8'))


class TelemetaWavImport:

    def __init__(self, source_dir, log_file, pattern):
        from django.contrib.auth.models import User
        self.logger = Logger(log_file)
        self.source_dir = source_dir
        self.collections = os.listdir(self.source_dir)
        self.pattern = pattern
        self.user = User.objects.filter(username='admin')[0]

    def write_file(self, item, wav_file, overwrite=False):
        filename = wav_file.split(os.sep)[-1]
        if os.path.exists(wav_file):
            if not item.file or overwrite:
                f = open(wav_file, 'r')
                file_content = ContentFile(f.read())
                item.file.save(filename, file_content)
                f.close()
                item.set_revision(self.user)
            else:
                msg = item.code + ' : fichier ' + item.file.name + ' deja inscrit dans la base de donnees !'
                self.logger.error('item', msg)
        else:
            msg = item.code + ' : fichier audio ' + filename + ' inexistant dans le dossier !'
            self.logger.error('item', msg)
            
    def wav_import(self):
        from telemeta.models import MediaItem,  MediaCollection
        
        for collection in self.collections:
            collection_dir = self.source_dir + os.sep + collection 
            collection_files = os.listdir(collection_dir)
            
            if not '/.' in collection_dir and self.pattern in collection_dir:
                collection_name = collection.split(os.sep)[-1]
                c = MediaCollection.objects.filter(code=collection_name)
                
                if not c and collection + '.csv' in collection_files:
                    msg = collection + ' collection NON présente dans la base de données, SORTIE '
                    self.logger.error(collection, msg)
                    sys.exit(msg)
                elif not c:
                    msg = 'collection NON présente dans la base de données, CREATION '
                    self.logger.info(collection, msg)
                    c = MediaCollection(code=collection_name)
                    c.save()
                    c.set_revision(self.user)
                else:
                    msg = 'collection présente dans la base de données'
                    self.logger.info(collection, msg)
                    
        for collection in self.collections:
            collection_dir = self.source_dir + os.sep + collection
            
            if not '/.' in collection_dir and self.pattern in collection_dir:
                collection_name = collection.split(os.sep)[-1]
                msg = '************************ ' + collection + ' ******************************'
                self.logger.info(collection, msg[:70])
                collection_files = os.listdir(collection_dir)
                
                if not collection + '.csv' in collection_files:
                    overwrite = False
                    msg = collection + ' pas de fichier CSV dans la collection'
                    self.logger.info(collection, msg[:70])
                    c = MediaCollection.objects.filter(code=collection_name)
                    
                    if not c:
                        c = MediaCollection(code=collection_name)
                        c.save()
                        msg = ' collection NON présente dans la BDD, CREATION '
                        self.logger.info(c.code, msg)
                        
                    else:
                        c = c[0]
                        msg = ' id = '+str(c.id)
                        self.logger.info(c.code, msg)
                        
                    for filename in collection_files:
                        wav_file = self.source_dir + os.sep + collection + os.sep + filename
                        code = filename.split('.')[0]
                        items = MediaItem.objects.filter(code=code)
                        
                        if len(items) != 0:
                            item = items[0]
                            msg = item.code + ' : id = '+str(item.id)
                            self.logger.info('item', msg)
                        else:
                            item = MediaItem(code=code, collection=c)
                            msg = item.code + ' : item NON présent dans la base de données, CREATION'
                            self.logger.info('item', msg)
                            
                        self.write_file(item, wav_file, overwrite)

                else:
                    overwrite = False
                    csv_file = self.source_dir + os.sep + collection + os.sep + collection + '.csv'
                    c = csv.reader(open(csv_file), delimiter=';')
                    
                    for row in c:
                        old_ref = row[0]
                        new_ref = row[1]
                        filename = new_ref + '.wav'
                        wav_file = self.source_dir + os.sep + collection + os.sep + filename
                        items = MediaItem.objects.filter(old_code=old_ref)
                
                        if items:
                            item = items[0]
                            msg = item.old_code + ' : id = ' + str(item.id)
                            self.logger.info('item', msg)
                            self.write_file(item, wav_file, overwrite)
                            item.code = new_ref
                            item.save()
                        else:
                            msg = old_ref + ' : item inexistant dans la base de données !'
                            self.logger.error('item', msg)


def print_usage(tool_name):
    print "Usage: "+tool_name+" <project_dir> <source_dir> <pattern> <log_file>"
    print "  project_dir: the directory of the Django project which hosts Telemeta"
    print "  source_dir: the directory containing the wav files to include"
    print "  pattern: a pattern to match the collection names"
    print "  log_file: a log file to write logs"

def run():
    if len(sys.argv) < 3:
        print_usage(os.path.basename(sys.argv[0]))
        sys.exit(1)
    else:
        project_dir = sys.argv[-4]
        source_dir = sys.argv[-3]
        pattern = sys.argv[-2]
        log_file = sys.argv[-1]
        sys.path.append(project_dir)
        import settings
        setup_environ(settings)
        t = TelemetaWavImport(source_dir, log_file, pattern)
        t.wav_import()

if __name__ == '__main__':
    run()
