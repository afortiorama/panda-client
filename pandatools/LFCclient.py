import re
import os
import sys

# error codes
EC_Main          = 70
EC_LFC           = 80

# import lfc api
try:
    import lfc
except:
    print "ERROR : could not import lfc"
    sys.exit(EC_LFC)


# get PFN from LFC
def _getPFNsLFC(guids,lfcHost,storages,verbose=False):
    # set LFC HOST
    os.environ['LFC_HOST'] = lfcHost
    # timeout
    os.environ['LFC_CONNTIMEOUT'] = '60'
    os.environ['LFC_CONRETRY']    = '2'
    os.environ['LFC_CONRETRYINT'] = '6'
                
    if verbose:
        print "get file info from %s" % lfcHost
    # get PFN
    iGUID = 0
    nGUID = 100
    pfnMap   = {}
    listGUID = []
    for guid in guids:
        if verbose:
            sys.stdout.write('.')
            sys.stdout.flush()
        iGUID += 1
        listGUID.append(guid)
        if iGUID % nGUID == 0 or iGUID == len(guids):
            # get replica
            ret,resList = lfc.lfc_getreplicas(listGUID,'')
            if ret == 0:
                for fr in resList:
                    if fr != None and ((not hasattr(fr,'errcode')) or \
                                       (hasattr(fr,'errcode') and fr.errcode == 0)):
                        # get host
                        match = re.search('[^:]+://([^:/]+):*\d*/',fr.sfn)
                        if match==None:
                            continue
                        # check host
                        host = match.group(1)
                        if storages != [] and (not host in storages):
                            continue
                        # append
                        if not pfnMap.has_key(fr.guid):
                            pfnMap[fr.guid] = []
                        pfnMap[fr.guid].append(fr.sfn)
            else:
                print "ERROR : %s" % lfc.sstrerror(lfc.cvar.serrno)
                sys.exit(EC_LFC)
            # reset                        
            listGUID = []
    # return
    return pfnMap
    


####################################################################
# main
def main():
    import sys
    import getopt
    # option class
    class _options:
        def __init__(self):
            pass
    options = _options()
    del _options
    # set default values
    options.verbose   = False
    options.infile    = ''
    options.lfchost   = ''
    options.storages  = []
    options.outfile   = ''    
    # get command-line parameters
    try:
        opts, args = getopt.getopt(sys.argv[1:],"s:i:vl:o:")
    except:
        _usage()
        print "ERROR : Invalid options"
        sys.exit(EC_Main)    
    # set options
    for o, a in opts:
        if o in ("-v",):
            options.verbose = True
        if o in ("-s",):
            options.storages = a.split(',')
        if o in ("-i",):
            options.infile = a
        if o in ("-o",):
            options.outfile = a
        if o in ("-l",):
            options.lfchost = a
    # read GUID/LFN
    ifile = open(options.infile)
    files = {}
    for line in ifile:
        items = line.split()
        if len(items) == 2:
            files[items[0]] = items[1]
    ifile.close()
    if options.verbose:
        print "GUID/LFN"
        print files
    # get pfns
    retFiles = _getPFNsLFC(files,options.lfchost,options.storages,options.verbose)
    if options.verbose:    
        print "\nPFNs : %s" % retFiles
    # write
    ofile = open(options.outfile,'w')
    ofile.write("%s" % retFiles)
    ofile.close()
    # return
    sys.exit(0)


if __name__ == "__main__":
    main()
        