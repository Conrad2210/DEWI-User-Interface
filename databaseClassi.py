import mysql.connector as mysql
import time

from sqlalchemy.sql.functions import current_date


class  databaseConnection():

    dbConnection = 0
    db = 'dewi_experiments';
    host = '157.190.53.108'
    #db = 'dewi_lwb'
    # db = 'dewi_flooding'
    def __init__(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
        except mysql.Error, e:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("CREATE DATABASE {0} DEFAULT CHARACTER SET 'utf8'".format(self.db))
            self.dbConnection.database =self.db
        try:            
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM experiments")
            for id in cursor:
                id
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE experiments (id INT NOT NULL, description TEXT NULL, date_time INT(11) NULL, PRIMARY KEY(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM settings")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE settings (id INT NOT NULL AUTO_INCREMENT, session_id INT NOT NULL, txPower TEXT NOT NULL, numberBursts INT NOT NULL, burstDuration INT NOT NULL, MSGPerBurst INT NOT NULL, PRIMARY KEY(id), FOREIGN KEY(session_id) REFERENCES dewi_experiments.experiments(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM latency")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE latency (id INT NOT NULL AUTO_INCREMENT, session_id INT NOT NULL,nodeID INT NOT NULL,timeslot INT NOT NULL, count INT NOT NULL, PRIMARY KEY(id), FOREIGN KEY(session_id) REFERENCES dewi_experiments.experiments(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM rxpackets")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE rxpackets (id INT NOT NULL AUTO_INCREMENT, session_id INT NOT NULL,nodeID INT NOT NULL,count INT NOT NULL, PRIMARY KEY(id), FOREIGN KEY(session_id) REFERENCES dewi_experiments.experiments(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM txpackets")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE txpackets (id INT NOT NULL AUTO_INCREMENT, session_id INT NOT NULL,nodeID INT NOT NULL,count INT NOT NULL, PRIMARY KEY(id), FOREIGN KEY(session_id) REFERENCES dewi_experiments.experiments(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM neighbours")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE neighbours (id INT NOT NULL AUTO_INCREMENT, session_id INT NOT NULL,parent INT NOT NULL,child INT NOT NULL,tier INT NOT NULL,colour INT NOT NULL, PRIMARY KEY(id), FOREIGN KEY(session_id) REFERENCES {0}.experiments(id))".format(self.db))
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
        try:
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT * FROM tempneighbours")
            for id in cursor:
                id
        
        except mysql.Error, e:
            try:
                self.dbConnection.cursor().execute("CREATE TABLE tempneighbours (id INT NOT NULL AUTO_INCREMENT,parent INT NOT NULL,child INT NOT NULL,tier INT NOT NULL,colour INT NOT NULL, PRIMARY KEY(id))")
            except IndexError:
                print "MySQL Error: %s" % str(e)

        self.dbConnection.close()
  
    
    def insertExperiment(self,id,description,date_time):        
        try:
            self.dbConnection = mysql.connect(host=self.host, user='root', password="root",
                                              db=self.db, buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("INSERT INTO experiments (id,description,date_time) VALUES ({0},'{1}',{2})").format(id,description,date_time))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "insertExperiment"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
  
    
    def insertSettings(self,id, session_id, txPower, numberBursts, burstDuration,MSGPerBurst,RSSIRadius):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("INSERT INTO settings(id, session_id, txPower, numberBursts, burstDuration,MSGPerBurst,RSSIRadius) VALUES ({0},{1},{2},{3},{4},{5},{6})").format(id, session_id, txPower, numberBursts, burstDuration,MSGPerBurst,RSSIRadius))
            self.dbConnection.commit()

            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "insertSettings"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def insertLatency(self,id, session_id, nodeID,timeslot,count):        
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("SELECT * FROM latency WHERE session_id = {0} AND nodeID = {1} AND timeslot = {2}").format(session_id, nodeID,timeslot))
            uniqe = True
            for row in cursor:
                uniqe = False     
                
            if uniqe == False:
                return
            cursor.execute(("INSERT INTO latency(id, session_id, nodeID,timeslot,count) VALUES ({0},{1},{2},{3},{4})").format(id, session_id, nodeID,timeslot,count))
            self.dbConnection.commit()

            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "insertLatency"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def insertRxPackets(self,id, session_id, nodeID,count):        
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("SELECT * FROM rxpackets WHERE session_id = {0} AND nodeID = {1}").format(session_id, nodeID))
            uniqe = True
            for row in cursor:
                uniqe = False     
                
            if uniqe == False:
                return
            cursor.execute(("INSERT INTO rxpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id, session_id, nodeID,count))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "insertRxPackets"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def insertTxPackets(self,id, session_id, nodeID,count):        
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("SELECT * FROM txpackets WHERE session_id = {0} AND nodeID = {1}").format(session_id, nodeID))
            uniqe = True
            for row in cursor:
                uniqe = False     
                
            if uniqe == False:
                return
            cursor.execute(("INSERT INTO txpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id, session_id, nodeID,count))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "insertTxPackets"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

    def insertTxPacketsParseFlockLab(self,id, session_id, nodeID,count):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("UPDATE txpackets SET count={0} WHERE session_id = {1} AND nodeID = {2}").format(count,session_id, nodeID))
            if cursor.rowcount == 0:
                cursor.execute(
                    ("INSERT INTO txpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id,
                                                                                                            session_id,
                                                                                                            nodeID,
                                                                                                            count))
            self.dbConnection.commit()
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:

                cursor.execute(
                    ("INSERT INTO txpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id,
                                                                                                            session_id,
                                                                                                            nodeID,
                                                                count))
                self.dbConnection.commit()
                self.dbConnection.close()
                print "insertTxPackets"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

    def insertRxPacketsParseFlockLab(self,id, session_id, nodeID,count):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("UPDATE rxpackets SET count={0} WHERE session_id = {1} AND nodeID = {2}").format(count,session_id, nodeID))
            if cursor.rowcount == 0:
                cursor.execute(
                    ("INSERT INTO rxpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id,
                                                                                                            session_id,
                                                                                                            nodeID,
                                                                                                            count))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:

                cursor.execute(
                    ("INSERT INTO rxpackets(id, session_id, nodeID,count) VALUES ({0},{1},{2},{3})").format(id,
                                                                                                            session_id,
                                                                                                            nodeID,
                                                                count))
                self.dbConnection.commit()
                self.dbConnection.close()
                print "insertTxPackets"
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def insertNeighbour(self,id,session_id, parent,child,tier,colour):        
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("INSERT INTO neighbours(id, session_id,parent,child,tier,colour) VALUES ({0},{1},{2},{3},{4},{5})").format(id,session_id, parent,child,tier,colour))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def insertTempNeighbour(self,id, parent,child,tier,colour):        
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("INSERT INTO tempneighbours(id, parent,child,tier,colour) VALUES ({0},{1},{2},{3},{4})").format(id,parent,child,tier,colour))
            self.dbConnection.commit()
            self.dbConnection.close()
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def getLastExperimentID(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute(("SELECT MAX(id) FROM experiments"))
            
            for id in cursor:
                if str(id[0]) == 'None':
                    self.dbConnection.close()
                    return -1
                else:
                    self.dbConnection.close()
                    return int(id[0])
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
        
        return 0
    def getNodeListParents(self,session_id):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT DISTINCT parent AS Number FROM neighbours WHERE session_id={0}".format(session_id))
            result = []
            for parent in cursor:
                result.append(hex(parent[0]))

            self.dbConnection.close()
            return result
        except mysql.Error, e:
            print "getLinkAddressList"
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
        return 0

    def getNodeListChilds(self,session_id,parent):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT DISTINCT child,colour AS Number FROM neighbours WHERE session_id={0} AND parent={1}".format(session_id,parent))
            result = []
            result.append([])
            result.append([])
            col = -1;
            for child,colour in cursor:
                result[0].append(hex(child))
                col = colour
            result[1].append(col)
            self.dbConnection.close()
            return result
        except mysql.Error, e:
            print "getLinkAddressList"
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
        return 0

    def getTopology(self,session_id):

        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT parent,child,tier,colour FROM neighbours WHERE session_id={0} ORDER BY tier ASC".format(session_id))
            #cursor.execute(
                # "SELECT parent,child FROM neighbours WHERE session_id={0} ORDER BY tier ASC".format(
                #     session_id))
            result = []
            result.append([])
            result.append([])
            for parent, child, tier, colour in cursor:
            # for parent, child in cursor:
            #     result[0].append((hex(parent), hex(child), tier, colour))
                uniqe = True
                for i in range(0, len(result[0])):
                    if result[0][i][1] == hex(child):
                        uniqe = False

                if uniqe == True:
                    result[0].append((hex(parent), hex(child), tier, colour))


            try:
                cursor = self.dbConnection.cursor()
                cursor.execute("SELECT DISTINCT parent AS Number FROM neighbours WHERE session_id={0}".format(session_id))

                for parent in cursor:
                    result[1].append(hex(parent[0]))
                cursor.execute("SELECT DISTINCT child AS Number FROM neighbours WHERE session_id={0}".format(session_id))
                for child in cursor:
                    uniqe = True
                    for i in range(0, len(result[1])):
                        if result[1][i] == hex(child[0]):
                            uniqe = False

                    if uniqe == True:
                        result[1].append(hex(child[0]))
                self.dbConnection.close()
                return result
            except mysql.Error, e:
                print "getLinkAddressList"
                try:
                    print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                except IndexError:
                    print "MySQL Error: %s" % str(e)

        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

        return 0


    def getAllNeighbours(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT parent,child,tier,colour FROM tempneighbours ORDER BY tier ASC")
            result = []
            for parent,child,tier,colour in cursor:
                result.append((hex(parent),hex(child),tier,colour))

            self.dbConnection.close()
            return result
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
        
        return 0
    
    def getLinkAddressList(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT DISTINCT parent AS Number FROM tempneighbours")
            result = []
            for parent in cursor:
                result.append(hex(parent[0]))
                
            
            cursor.execute("SELECT DISTINCT(child) AS Number FROM tempneighbours") 
            for child in cursor:
                uniqe=True
                for i in range(0,len(result)):
                    if result[i] == hex(child[0]):
                        uniqe=False
                        
                if uniqe==True:
                    result.append(hex(child[0]))

            self.dbConnection.close()
            return result
        except mysql.Error, e:
            print "getLinkAddressList"
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)
        
        return 0
    
    def clearTempNeighbourList(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("TRUNCATE tempneighbours")
 
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

        self.dbConnection.close()
        return 0
        
    def saveNeighbours(self): 
           
        result = self.getAllNeighbours()
        id = self.getLastExperimentID()
        for i in range(0,len(result)):
            self.insertNeighbour(0,id,result[i][0],result[i][1],result[i][2],result[i][3])
            
    def getExperiments(self):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT description, date_time FROM experiments")
            descriptionRes = []
            for description, date_time in cursor:
                descriptionRes.append((str(description),str(date_time)))
            settingsRes = []
            cursor.execute("SELECT session_id,numberBursts,burstDuration,MSGPerBurst, TXPower, RSSIRadius FROM settings")
            for session_id,numberBursts,burstDuration,MSGPerBurst,TXPower, RSSIRadius in cursor:
                settingsRes.append((session_id,numberBursts,burstDuration,MSGPerBurst,TXPower, RSSIRadius))


            completeRes = []
            for i in range(0,len(settingsRes)):
                completeRes.append((descriptionRes[i][0],settingsRes[i][0],settingsRes[i][1],settingsRes[i][2],settingsRes[i][3],settingsRes[i][4],settingsRes[i][5],descriptionRes[i][1]))

            self.dbConnection.close()
            return completeRes
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
                return [];
            except IndexError:
                print "MySQL Error: %s" % str(e)
                
    def getLatencyResult(self,session_id):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT timeslot,count FROM latency WHERE session_id={0} ORDER BY timeslot ASC".format(session_id))
            latencyRes = []
            for timeslot,count in cursor:
                latencyRes.append((int(timeslot),int(count)))


            self.dbConnection.close()
            return latencyRes
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

    def getDescription(self,session_id):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT legend_text FROM experiments WHERE id={0}".format(session_id))
            descriptionRes = []
            for description in cursor:
                descriptionRes.append(str(description[0]))

            self.dbConnection.close()
            return descriptionRes
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)


    def getTXPackets(self,session_id):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT count FROM txpackets WHERE session_id={0}".format(session_id))
            latencyRes = []
            for count in cursor:
                latencyRes.append(int(count[0]))

            self.dbConnection.close()
            return latencyRes
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)                
    def getRXPackets(self,session_id):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT count FROM rxpackets WHERE session_id={0}".format(session_id))
            latencyRes = []
            for count in cursor:
                latencyRes.append(int(count[0]))

            self.dbConnection.close()
            return latencyRes
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

    def getRXPacketsForNode(self,session_id,addr):
        try:
            self.dbConnection = mysql.connect(host=self.host,user='root',password="root",db=self.db,buffered=True)
            cursor = self.dbConnection.cursor()
            cursor.execute("SELECT count FROM rxpackets WHERE session_id={0} AND nodeID={1}".format(session_id,addr))
            latencyRes = []
            for count in cursor:
                self.dbConnection.close()
                return count[0]
        except mysql.Error, e:
            try:
                print "MySQL Error [%d]: %s" % (e.args[0], e.args[1])
            except IndexError:
                print "MySQL Error: %s" % str(e)

    def returnHex(self,text):
        try:
            return hex(text)
        except TypeError, e:
            print e;

dewi = databaseConnection()
# #
# print dewi.clearTempNeighbourList()
#
# print dewi.getNodeListParents(60)
# print dewi.getNodeListChilds(60,dewi.getNodeListParents(60)[2])