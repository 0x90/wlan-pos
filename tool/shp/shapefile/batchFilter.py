import sys
import os
import tablefilter

def batchFilter(infolder,infiles,field,prefix="",filestem=True,enum=False,outfolder="",retype=False,remove=True,equal="#",minimum="#",maximum="#"):
    for id,f in enumerate(infiles):
        outfile=""
        if outfolder=="":
            outfile=infolder
        else:
            outfile=outfolder
        outfile=outfile+"\\"+prefix
        if filestem:
            outfile=outfile+f[:f.rfind(".")]
        if enum:
            outfile=outfile+str(id)
        outfile=outfile+".dbf"
        infile=infolder+"\\"+f
        tablefilter.filterTable(infile,outfile,field,remove,equal,minimum,maximum,retype)
        

if __name__=="__main__":
    infolder=sys.argv[1]
    infiles=os.listdir(infolder)
    if sys.argv[2]=="#":
        prefix=""
    else:
        prefix=sys.argv[2]
    if sys.argv[3]=="true":
        filestem=True
    else:
        filestem=False
    if sys.argv[4]=="true":
        enum=True
    else:
        enum=False
    if sys.argv[5]=="#":
        folder=""
    else:
        folder=sys.argv[5]
    if sys.argv[6]=="true":
        dynamicSpecs=True
    else:
        dynamicSpecs=False
    field=sys.argv[7]
    if sys.argv[8]=="true":
        remove=True
    else:
        remove=False
    equal=sys.argv[9]
    minimum=sys.argv[10]
    maximum=sys.argv[11]
    if sys.argv[12]=="true":
        retype=True
    else:
        retype=False
    
    batchFilter(infolder,infiles,field,prefix,filestem,enum,folder,retype,remove,equal,minimum,maximum)