from workspace import Workspace
from logger import Logger
from LocalLocation import LocalLocation
from pathlib import Path
from dvengine import DvEngine
from DevEntity import DevEntity
from link import Link
from dbServer import DbServer
from postgreDbServer import PostgreDbServer
from Hub import Hub
from satellite import Satellite
import os
from pathlib import Path
import re

class Lambda:

    def __init__(self,LocalLocation, PostgreDbServer, Logger):
       
        self.Logger = Logger
        self.LocalLocation = LocalLocation
        self.PostgreDbServer = PostgreDbServer
        self.Workspace = None
        self.files_name = None
        self.log_format = None
        self.file_repository = None
        self.archive_repository = None
        self.error_repository = None
        self.log_repository = None
       

    def setRepositories(self):
        workspaces = []
        local = self.LocalLocation
        if os.path.exists('repository_config.yml'):
            list_workspace, list_repo = local.readConfigFile('repository_config.yml')
        if os.path.isdir(list_repo['archive_repo']):
            self.archive_repository = list_repo['archive_repo']
        if os.path.isdir(list_repo['error_repo']):
            self.error_repository = list_repo['error_repo']
        if os.path.isdir(list_repo['log_repo']):
            self.log_repository = list_repo['log_repo']
        for workspace in list_workspace:
            self.files_name = self.extractFile(workspace.repository)
            self.Workspace = Workspace(workspace.repository)
            self.Workspace.set_fileNames(self.files_name)
               
        message = "Started reading my Repository"
        self.Logger.debug(message)

    def load_data(self) :
        local = self.LocalLocation
        #link = Link()
        dvengine = DvEngine(None, None)
        postgre = self.PostgreDbServer
        self.Logger.debug("Let's establish a connection with the DbServer")
        database = postgre.connectTOdb("postgres", "root")
        if postgre.checkIfDBexists(database, 'yellow_tripdata')[0] != 'OK':
            postgre.executeRequest(database, dvengine.getSqlQueryCreateDb('yellow_tripdata'))
            self.Logger.debug("I created the Database {}".format(self.files_name[0].rsplit("_", 1)[0]))
        
        try:
            db_name = 'yellow_tripdata'
            suffix = self.files_name[0].split("_", 2)[1]
            database = postgre.connectTOdbComplete(db_name,"postgres", "root")
            postgre.executeRequest(database, dvengine.getSqlQueryCreateSchema('Staging'))
            print(postgre.checkIfTableExists(database, 'stg_'+suffix))
            print(postgre.checkIfTableExists(database, 'tmp'))
            if postgre.checkIfTableExists(database, 'stg_'+suffix) != 'OK':
                request2 = dvengine.getSqlQueryCreateStaging(self.Workspace.repository, self.files_name[0], 'Staging')
                postgre.executeRequest(database, request2)
                self.Logger.debug("I created the Staging{}".format(suffix))
            path = self.Workspace.repository
            for file_name in self.Workspace.fileNames:
                file_name = os.path.basename(file_name)
                print(file_name)
                postgre.loadFile(database, path+'\\'+file_name, 'staging' , 'stg_'+suffix, ',')
            postgre.executeRequest(database, dvengine.getSqlQueryCreateSchema('raw_dv'))
            list_hubs, list_satellites, list_links = local.readObjectFile("object_config.yml")
            message = "Started reading my Objects"
            self.Logger.debug(message)
            message= 'I found {} HUB, {} Satellite'.format(len(list_hubs), len(list_satellites))
            self.Logger.debug(message)
            for entity in list_hubs:
                print('new one')
                name = entity.name.removeprefix('HUB_')
                hub = Hub(entity.name, entity.business_key, entity.fields)
                print(hub)
                dvengine = DvEngine(hub, None)
                if postgre.checkIfTableExists(database, entity.name.lower()) != 'OK':
                    request1 = dvengine.getSqlQueryCreateDevEntity('raw_dv', None)
                    postgre.executeRequest(database, request1)
                    self.Logger.debug("I created the {}".format(entity.name))
                request = dvengine.insertiORupdateEntity(file_name)
                postgre.executeRequest(database, dvengine.insertiORupdateEntity(file_name))
            for entity in list_satellites:
                name = entity.name.removeprefix('SAT_')
                sat = Satellite(entity.name, entity.business_key, entity.fields)
                dvengine = DvEngine(sat, None)
                if postgre.checkIfTableExists(database, entity.name.lower()) != 'OK':
                    request1 = dvengine.getSqlQueryCreateDevEntity('raw_dv', None)
                    postgre.executeRequest(database, request1)
                postgre.executeRequest(database, dvengine.insertiORupdateEntity(file_name))
                dvengine.insertiORupdateEntity(file_name)
                self.Logger.debug("I created the {}".format(entity.name))

            
            #postgre.truncatestagingTable(database, 'staging.stg_'+suffix)
            #for file_name in self.Workspace.fileNames:
             #   local.copyFile(self.Workspace.repository+'\\'+file_name, self.archive_repository+'\\'+file_name)


        except Exception as e:
            self.Logger.error("ERROR:{}".format(e))
            #for file_name in self.Workspace.fileNames:
            #    local.copyFile(self.Workspace.repository+'\\'+file_name, self.error_repository+'\\'+file_name)
            raise
               
            

    def extractFile(self, repository):
        list_files = []
        for file in os.listdir(repository):
            match = re.search("\.csv$", file)
            if match :
                list_files.append(file)
        return list_files  