"""The datbasefile class.

This class expands on the writer and reader created by Raymond Hettinger.

See http://code.activestate.com/recipes/362715/
"""
__author__ = "Martin Lacayo-Emery <positrons@gmail.com>"
__date__ = "23 November 2006"

__credits__ = """Arzu \xc7\xf6ltekin, University of Z\xfcrich, project collaborator
Sara Fabrikant, University of Z\xfcrich, project collaborator
Andr\xe9 Skupin, San Diego State University, thesis advisor
University of Z\xfcrich, host institution
San Diego State University, home institution
Eidgen\xf6ssischen Stipendienkommission f\xfcr ausl\xe4ndische Studierende, host funding agency
Fulbright Program, host funding program
Department of Geography, San Diego State University, home funding
"""
import struct
import datetime
import decimal
import itertools
import string

#helper functions
def spec(valueString):
    """
    spec(valueString) accepts a string and returns the data type, width, and precision.
    The results are the smallest of each data type, width, and precision that can store the input.

    >>> spec("1")
    ('N', 1, 0)
    >>> spec("-1")
    ('N', 2, 0)
    >>> spec("1.0")
    ('N', 3, 2)
    >>> spec("-1.0")
    ('N', 4, 2)
    >>> spec("1.0Q")
    ('C', 4, 0)
    >>> spec("-1.0Q")
    ('C', 5, 0)
    """
##    number=False
##    decimal=False
##    negative=False
##    for c in valueString.strip():
##        if c in string.digits:
##            if not number:
##                number=True
##        elif c == "." and not decimal:
##            decimal=True
##        elif c=="-" and not negative:
##            negative=True
##        else:
##            return ("C",len(valueString),0)
##    if decimal:
##        return ("N",len(valueString),len(valueString)-valueString.rfind("."))
##    else:
##        return ("N",len(valueString),0)
    valueString=str(valueString)
    try:
        int(valueString)
        return ("N",len(valueString),0)
    except ValueError:
        try:
            float(valueString)
            return ("N",len(valueString),len(valueString)-valueString.rfind("."))
        except ValueError:
            return ("C",len(valueString),0)

def specType(specvalue):
    if specvalue[0]=="C":
        return str
    elif specvalue[0]=="N":
        if specvalue[2]==0:
            return int
        else:
            return float
    return None

def typelist(specList):
    """
    typelist(specList) accepts a list of specs and returns their Python types
    >>> typelist([('N',1,0),('N',1,2),('C',5,0)])
    [<type 'int'>, <type 'float'>, <type 'str'>]
    """
    l=[]
    for t,w,d in specList:
        if t == "N":
            if d==0:
                l.append(int)
            else:
                l.append(float)
        else:
            l.append(str)
    return l
        
##def mapapply(mapapplylist):
##    """
##    mapapply(mapapplylist) accepts a list of lists,
##    each element in the list is a list begining with a function followed by parameters
##    the fucntion is called with the remainging list items
##
##    >>> mapapply([(int,"1"), (float,"1.0"), (str, 4)])
##    [1, 1.0, "4"]
##    """
##    l=[]
##    for m in mapapplylist:
##        l.append(apply(apply,m))
##    return l


def integratespecs(s1,s2):
    """
    integratespecs(s1,s2) takes two lists of specs and integrates them.
    The result is a single list the contains specs compatible with both lists.

    >>> integratespecs([("N",2,0),("N",4,2),("N",2,0)],[("N",4,0),("N",4,0),("C",4,0)])
    [('N', 4, 0), ('N', 6, 2), ('C', 4, 0)]
    """
    s3=[]
    for s in zip(s1,s2):
        #if either charater type
        if s[0][0]=="C" or s[1][0]=="C":
            #pick the longer of the two
            if s[0][1]>s[1][1]:
                s3.append(("C",s[0][1],0))
            else:
                s3.append(("C",s[1][1],0))
            
        else:
            whole=max([s[0][1]-s[0][2],s[1][1]-s[1][2]])
            fract=max([s[0][2],s[1][2]])
            s3.append(("N",whole+fract,fract))
    return s3



class DatabaseFile:
    """
    DatabaseFile is a class that stores a DBF file

    >>> d=DatabaseFile([],[],[])
    >>> d.addField('ID',("N",1,0))
    >>> d.fieldnames
    ['ID']
    >>> d=DatabaseFile(["Int","Float","String"],[("N",5,0),("N",5,3),("C",5,0)],[[12345,12.45,"12345"]])
    >>> d.refreshSpecs()
    >>> d.fieldspecs
    [('N', 5, 0), ('N', 5, 3), ('N', 5, 0)]
    >>> d.addRow(["Hello","World", "!"])
    >>> d.refreshSpecs()
    >>> d.fieldspecs
    [('C', 5, 0), ('C', 5, 0), ('C', 5, 0)]
    >>> d.records.pop(1)
    ['Hello', 'World', '!']
    >>> d.refreshSpecs()
    >>> d.fieldspecs
    [('N', 5, 0), ('N', 5, 3), ('N', 5, 0)]
    >>> fieldnames=["Int","Float","String"]
    >>> fieldspecs=[("N",5,0),("N",5,3),("C",13,0)]
    >>> records=[["12345","12.45","one two three"]]
    >>> d=DatabaseFile(fieldnames,fieldspecs,records)
    >>> d.refreshSpecs()
    >>> import tempfile
    >>> dbf=tempfile.TemporaryFile()
    >>> d.write(dbf)
    >>> dbf.seek(0,0)
    >>> e=DatabaseFile([],[],[])
    >>> e.records=list(e.read(dbf))
    >>> e.fieldnames=e.records.pop(0)
    >>> e.fieldspecs=e.records.pop(0)
    >>> e.fieldnames==fieldnames
    True
    >>> e.fieldspecs==fieldspecs
    True
    >>> e.records==records
    True
    >>> dbf.close()
    """
    def __init__(self,fieldnames,fieldspecs,records,dbffile=None):
        if dbffile==None:
            self.fieldnames=fieldnames
            self.fieldspecs=fieldspecs
            self.records=records
        else:
            self.readFile(dbffile)

    def __len__(self):
        return len(self.records)

    #accessors

    def __getitem__(self,i):
        return self.records[i]

    def index(self,s):
        return self.fieldnames.index(s)

    def find(self,fieldIndex,value):
        value=str(value).strip()
        for id,row in enumerate(self.records):
            if row[fieldIndex].strip()==value:
                return id
        raise ValueError, "Value \""+value+"\" not found."
    
    #modifiers
    def typecast(self):
        casting=typelist(self.fieldspecs)
        for rowID,row in enumerate(self.records):
            for colID,value in enumerate(row):
                self.records[rowID][colID]=casting[colID](value)
            
    def staticSpecs(self):
        """
        staticSpecs sets the current fieldspecs to all be strings of  the minimum width supporting the current data.
        """
        self.fieldspecs=[("C",w,0) for w in map(max,apply(zip,[map(len,l) for l in self.records]))]

    def dynamicSpecs(self):
        """
        """
        self.refreshSpecs()

    def refreshSpecs(self):
        """

        """
        #if rows in table
        if len(self.records) > 0:
            specs=map(spec,map(str,self.records[0]))
            for l in self.records[1:]:
                specs=integratespecs(specs,map(spec,map(str,l)))
            self.fieldspecs=specs

    def extend(self,other):
        """
        extends each row with the row of another table
        """
        if len(self.records)!=len(other.records):
            raise ValueError, "The number of rows do not match."

        self.fieldnames.extend(other.fieldnames)
        self.fieldspecs.extend(other.fieldspecs)
        for i in range(len(self.records)):
            self.records[i].extend(other.records[i])

    def append(self,other):
        """
        appends all the rows from another table to this table
        """
        if len(self.fieldnames)!=len(other.fieldnames):
            raise ValueError, "The number of columns do not match."

        self.fieldspecs=integratespecs(self.fieldspecs,other.fieldspecs)
        self.records.extend(other.records)
        
    def addField(self,fieldname,fieldspec):
        self.fieldnames.append(fieldname)
        self.fieldspecs.append(fieldspec)
        for row in self.records:
            row.append("")            

    def addColumn(self,fieldname,fieldspec,record):
        if len(record)!=len(self.records):
            raise ValueError,"The column length does not match the current table."
        self.fieldnames.append(fieldname)
        self.fieldspecs.append(fieldspec)
        for id,r in enumerate(record):
            self.records[id].extend(r)

    def addRow(self,record):
        if len(record)==len(self.fieldnames):
            self.records.append(record)
        else:
            raise ValueError, "The record does have the same number of columns as the table."

    def removeColumn(self,columnIndex):
        self.fieldnames.pop(columnIndex)
        self.fieldspecs.pop(columnIndex)
        column=[]
        for row in self.records:
            column.append(row.pop(columnIndex))
        return column

    def removeRow(self,rowIndex):
        return self.records.pop(rowIndex)

    def addFileColumn(self, inName,colName):
        """
        Appends a column form a DBF file to the current table.
        """
        f=open(inName,"rb")
        numrec, lenheader = struct.unpack('<xxxxLH22x', f.read(32))    
        numfields = (lenheader - 33) // 32

        fields = []
        for fieldno in xrange(numfields):
            name, typ, size, deci = struct.unpack('<11sc4xBB14x', f.read(32))
            name = name.replace('\0', '')       # eliminate NULs from string   
            fields.append((name, typ, size, deci))
        #yield [field[0] for field in fields]
        #yield [tuple(field[1:]) for field in fields]

        f.seek(2,1)

        fields=apply(zip,fields)
        columnIndex=list(fields[0]).index(colName)
        seeklength1=sum(fields[2][:columnIndex-1])+1
        readlength=fields[2][columnIndex]
        seeklength2=sum(fields[2][columnIndex+1:])+1

        self.fieldnames.append(fields[0][columnIndex])
        self.fieldspecs.append((fields[1][columnIndex],fields[2][columnIndex],fields[3][columnIndex]))
        for i in xrange(numrec):
            if i > len(self.records)-1:
                self.records.append([])
            f.seek(seeklength1,1)
            self.records[i].append(f.read(readlength))
            f.seek(seeklength2,1)

    def select(self,fieldIndex,equal=None,minimum=None,maximum=None,selection=True):
        #get field type for typecasting comparisons
        fieldType=specType(self.fieldspecs[fieldIndex])

        #typecast compartors, just in case
        if equal != None:
            equal=fieldType(equal.strip())
        if minimum != None:
            minimum=fieldType(minimum.strip())
        if maximum!=None:
            maximum=fieldType(maximum.strip())
            
        #apply criteria    
        if selection:
            for i in range(len(self)-1,-1,-1):
                temp=fieldType(self.records[i][fieldIndex].strip())
                if equal != None and temp == equal:
                    pass
                elif minimum != None and temp < minimum:
                    self.records.pop(i)
                elif maximum != None and temp > maximum:
                    self.records.pop(i)
        else:
            for i in range(len(self)-1,-1,-1):
                temp=fieldType(self.records[i][fieldIndex].strip())
                if equal != None and temp == equal:
                    self.records.pop(i)
                elif minimum != None and temp <= minimum:
                    self.records.pop(i)
                elif maximum != None and temp >= maximum:
                    self.records.pop(i)            

        
        

    #i/o

    def readFile(self,inName):
        """
        readFile reads a DBF file from the specified path        
        """        
        inFile=open(inName,'rb')
        self.records=list(self.read(inFile))
        self.fieldnames=self.records.pop(0)
        self.fieldspecs=self.records.pop(0)
        inFile.close()

    def readSV(self,inName,separator):
        inFile=open(inName,'r')
        self.fieldnames=inFile.readline().strip().split(separator)
        self.records=[row.strip().split(separator) for row in inFile.readlines()]
        inFile.close()
        self.staticSpecs()

    def readCSV(self,inName):
        self.readSV(inName,",")
        
    def readTSV(self,inName):
        self.readSV(inName,"\t")
    
    def read(self,f):
        """Returns an iterator over records in a Xbase DBF file.

        The first row returned contains the field names.
        The second row contains field specs: (type, size, decimal places).
        Subsequent rows contain the data records.
        If a record is marked as deleted, it is skipped.

        File should be opened for binary reads.

        """
        # See DBF format spec at:
        #     http://www.pgts.com.au/download/public/xbase.htm#DBF_STRUCT

        numrec, lenheader = struct.unpack('<xxxxLH22x', f.read(32))    
        numfields = (lenheader - 33) // 32

        fields = []
        for fieldno in xrange(numfields):
            name, typ, size, deci = struct.unpack('<11sc4xBB14x', f.read(32))
            name = name.replace('\0', '')       # eliminate NULs from string   
            fields.append((name, typ, size, deci))
        yield [field[0] for field in fields]
        yield [tuple(field[1:]) for field in fields]

        terminator = f.read(1)
        assert terminator == '\r'

        fields.insert(0, ('DeletionFlag', 'C', 1, 0))
        fmt = ''.join(['%ds' % fieldinfo[2] for fieldinfo in fields])
        fmtsiz = struct.calcsize(fmt)
        for i in xrange(numrec):
            record = struct.unpack(fmt, f.read(fmtsiz))
            if record[0] != ' ':
                continue                        # deleted record
            result = []
            for (name, typ, size, deci), value in itertools.izip(fields, record):
                if name == 'DeletionFlag':
                    continue
                if typ == "N":
                    value = value.replace('\0', '').lstrip()
                    #keep as string
##                    if value == '':
##                        value = 0
##                    elif deci:
##                        value = decimal.Decimal(value)
##                    else:
##                        value = int(value)
                elif typ == 'D':
                    y, m, d = int(value[:4]), int(value[4:6]), int(value[6:8])
                    value = datetime.date(y, m, d)
                elif typ == 'L':
                    value = (value in 'YyTt' and 'T') or (value in 'NnFf' and 'F') or '?'
                result.append(value)
            yield result

    def writeFile(self,outName):
        """
        writeFile writes a DBF file to the specified path
        """
        outFile=open(outName,'wb')
        self.write(outFile)
        outFile.close()

    def write(self,f):
        """ Return a string suitable for writing directly to a binary dbf file.

        File f should be open for writing in a binary mode.

        Fieldnames should be no longer than ten characters and not include \x00.
        Fieldspecs are in the form (type, size, deci) where
            type is one of:
                C for ascii character data
                M for ascii character memo data (real memo fields not supported)
                D for datetime objects
                N for ints or decimal objects
                L for logical values 'T', 'F', or '?'
            size is the field width
            deci is the number of decimal places in the provided decimal object
        Records can be an iterable over the records (sequences of field values).
        
        """
        #remove invlaid characters
        charmap=string.maketrans(string.punctuation.replace("_","")+string.whitespace,
                             " "*(len(string.punctuation)+len(string.whitespace)-1))
        self.fieldnames=[fieldname.translate(charmap).replace(" ","") for fieldname in self.fieldnames]

        #count number of field name stems
        nameset=set([name[:10] for name in self.fieldnames])
        namedict=dict(zip(nameset,[0]*len(nameset)))
        countdict=dict(zip(nameset,[0]*len(nameset)))
        for name in self.fieldnames:
            stem=name[:10]
            namedict[stem]=namedict[stem]+1
            countdict[stem]=countdict[stem]+1
        
        #enumerate column names if necessary
        tempnames=self.fieldnames
        tempnames.reverse()
        for id,name in enumerate(tempnames):
            stem=name[:10]
            if namedict[stem]>1:
                tempnames[id]=stem[:9]+str(countdict[stem])
                countdict[stem]=countdict[stem]-1
            else:
                tempnames[id]=stem
        tempnames.reverse()
        self.fieldnames=tempnames

        # header info
        ver = 3
        now = datetime.datetime.now()
        yr, mon, day = now.year-1900, now.month, now.day
        numrec = len(self.records)
        numfields = len(self.fieldspecs)
        lenheader = numfields * 32 + 33
        lenrecord = sum(field[1] for field in self.fieldspecs) + 1
        hdr = struct.pack('<BBBBLHH20x', ver, yr, mon, day, numrec, lenheader, lenrecord)
        f.write(hdr)
                          
        # field specs
        for name, (typ, size, deci) in itertools.izip(self.fieldnames, self.fieldspecs):
            name = name.ljust(11, '\x00')
            fld = struct.pack('<11sc4xBB14x', name, typ, size, deci)
            f.write(fld)

        # terminator
        f.write('\r')

        # records
        for record in self.records:
            f.write(' ')                        # deletion flag
            for (typ, size, deci), value in itertools.izip(self.fieldspecs, record):
                if typ == "N":
                    value = str(value).rjust(size, ' ')
                elif typ == 'D':
                    value = value.strftime('%Y%m%d')
                elif typ == 'L':
                    value = str(value)[0].upper()
                else:
                    value = str(value)[:size].ljust(size, ' ')
                try:
                    assert len(value) == size
                except AssertionError:
                    raise AssertionError, "value "+str(value)+" is no good "+str(size)
                f.write(value)

        # End of file
        f.write('\x1A')

    def writeSV(self,outName,separator,alternate=""):
        outFile=open(outName,'w')
        for row in self.records:
            outFile.write(separator.join([f.strip().replace(separator,alternate) for f in row])+",\n")
        outFile.close()
                
    def writeCSV(self,outName):
        self.writeSV(outName,", ")
            
if __name__ == "__main__":
    import doctest
    print
    doctest.testmod()

