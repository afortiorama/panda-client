import os
import re
import commands

# replace parameter with compact LFNs
def replaceParam(patt,inList,tmpJobO):
    # remove attempt numbers
    compactLFNs = []
    for tmpLFN in inList:
        compactLFNs.append(re.sub('\.\d+$','',tmpLFN))
    # sort
    compactLFNs.sort()
    # replace parameters
    if len(compactLFNs) < 2:
        # replace for single input
        tmpJobO = tmpJobO.replace(patt,compactLFNs[0])
    else:
        # find head and tail to convert file.1.pool,file.2.pool,file.4.pool to file.[1,2,4].pool
        tmpHead = ''
        tmpTail = ''
        tmpLFN0 = compactLFNs[0]
        tmpLFN1 = compactLFNs[1]
        for i in range(len(tmpLFN0)):
            match = re.search('^(%s)' % tmpLFN0[:i],tmpLFN1)
            if match:
                tmpHead = match.group(1)
            match = re.search('(%s)$' % tmpLFN0[-i:],tmpLFN1)
            if match:
                tmpTail = match.group(1)
        # remove numbers : ABC_00,00_XYZ -> ABC_,_XYZ
        tmpHead = re.sub('\d*$','',tmpHead)
        tmpTail = re.sub('^\d*','',tmpTail)
        # create compact paramter
        compactPar = '%s[' % tmpHead
        for tmpLFN in compactLFNs:
            # extract number
            tmpLFN = re.sub('^%s' % tmpHead,'',tmpLFN)
            tmpLFN = re.sub('%s$' % tmpTail,'',tmpLFN)
            compactPar += '%s,' % tmpLFN
        compactPar = compactPar[:-1]
        compactPar += ']%s' % tmpTail
        # replace
        tmpJobO = tmpJobO.replace(patt,compactPar)
    # return
    return tmpJobO


# get references from collection
def getGUIDfromColl(athenaVer,inputColls,directory,refName='Token',verbose=False):
    allrefs = []
    refs = {}
    # supported with 14.3.0 and onward
    if athenaVer != 'dev' and athenaVer < '14.4.0':
        print "WARNING : getGUIDfromColl is not supported in %s" \
              % athenaVer
        return refs,allrefs
    # extract refereces
    for inputColl in inputColls:
        refs[inputColl] = []
        com = "CollListFileGUID.exe -queryopt %s -src PFN:%s/%s RootCollection" % \
              (refName,directory,inputColl)
        if verbose:
            print com
        status,out = commands.getstatusoutput(com)
        if verbose:
            print status,out
        if status != 0:
            raise RuntimeError,"ERROR : failed to run %s" % com
        # get GUIDs
        for line in out.split('\n'):
            items = line.split()
            # confirm GUID format
            guid = items[-1]
            if re.search('^\w{8}-\w{4}-\w{4}-\w{4}-\w{12}$',guid):
                refs[guid] = inputColl
                allrefs.append(guid)
    # return
    return refs,allrefs


# convert list of files to compact format : header[body]tailer[attemptNr]
def convToCompact(fList):
    # no conversion
    if len(fList) == 0:
        return ''
    elif len(fList) == 1:
        return '%s' % fList[0]
    # get header
    header = fList[0]
    for item in fList:
        # look for identical sub-string
        findStr = False
        for idx in range(len(item)):
            if idx == 0:
                subStr = item
            else:
                subStr = item[:-idx]
            # compare
            if re.search('^%s' % subStr, header) != None:
                # set header
                header = subStr
                findStr = True
                break
        # not found
        if not findStr:
            header = ''
            break
    # get body and attemptNr
    bodies = []
    attNrs = []
    for item in fList:
        body  = re.sub('^%s' % header,'',item)
        attNr = ''
        # look for attNr
        match = re.search('(.+)(\.\d+)$',body)
        if match != None:
            body  = match.group(1)
            attNr = match.group(2)
        # append    
        bodies.append(body)
        attNrs.append(attNr)
    # get tailer
    tailer = bodies[0]
    for item in bodies:
        # look for identical sub-string
        findStr = False
        for idx in range(len(item)):
            subStr = item[idx:]
            # compare
            if re.search('%s$' % subStr, tailer) != None:
                # set tailer
                tailer = subStr
                findStr = True
                break
        # not found
        if not findStr:
            tailer = ''
            break
    # remove tailer from bodies
    realBodies = []
    for item in bodies:
        realBody = re.sub('%s$' % tailer,'',item)
        realBodies.append(realBody)
    bodies = realBodies    
    # convert to string
    retStr = "%s%s%s%s" % (header,bodies,tailer,attNrs)
    # remove whitespaces and '
    retStr = re.sub('( |\'|\")','',retStr)
    return retStr


# get Athena version
def getAthenaVer():
    # get project parameters
    out = commands.getoutput('cmt show projects')
    lines = out.split('\n')
    # remove CMT warnings
    tupLines = tuple(lines)
    lines = []
    for line in tupLines:
        if not line.startswith('#'):
            lines.append(line)
    if len(lines)<2:
        print out
        print "ERROR : cmt show projects"
        return False,{}

    # private work area
    res = re.search('\(in ([^\)]+)\)',lines[0])
    if res==None:
        print lines[0]
        print "ERROR : could not get path to private work area"
        return False,{}
    workArea = os.path.realpath(res.group(1))

    # get Athena version and group area
    athenaVer = ''
    groupArea = ''
    cacheVer  = ''
    nightVer  = ''
    for line in lines[1:]:
        res = re.search('\(in ([^\)]+)\)',line)
        if res != None:
            items = line.split()
            if items[0] in ('dist','AtlasRelease','AtlasOffline'):
                # Atlas release
                athenaVer = os.path.basename(res.group(1))
                # nightly
                if athenaVer.startswith('rel'):
                   if re.search('/bugfix',line) != None:
                      nightVer  = '/bugfix'
                   elif re.search('/dev',line) != None:
                      nightVer  = '/dev'
                   else:
                      print "ERROR : unsupported nightly %s" % line
                      return False,{}
                break
            elif items[0] in ['AtlasProduction','AtlasPoint1','AtlasTier0','AtlasP1HLT']:
                # production cache
                cacheVer = '-%s_%s' % (items[0],os.path.basename(res.group(1)))
            else:
                # group area
                groupArea = os.path.realpath(res.group(1))
    # pack return values
    retVal = {
        'workArea' : workArea,
        'athenaVer': athenaVer,
        'groupArea': groupArea,
        'cacheVer' : cacheVer,
        'nightVer' : nightVer,
           }
    # return
    return True,retVal