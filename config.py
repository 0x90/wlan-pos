DATPATH = 'dat/'
RAWSUFFIX = '.raw'
RMPSUFFIX = '.rmp'
INTERSIZE = 10
CLUSTERKEYSIZE = 4
KNN = 4
# String length of 179 and 149 chars are used for each intersection set to have 
# at most INTERSET APs, which should be enough for classification, very ugly though.
dt_rmp_nocluster = {'names':('spid','lat','lon','macs','rsss'), 
                       'formats':('i4','f4','f4','S179','S149')}
WLAN_FAKE = {
        2: #home
           [ ['00:25:86:23:A4:48', '-86'], ['00:24:01:FE:0F:20', '-90'], 
             ['00:0B:6B:3C:75:34', '-89'] ],
        1: #cmri
           [ ['00:11:B5:FD:8B:6D', '-79'], ['00:15:70:9E:91:60', '-52'], 
             ['00:15:70:9E:91:61', '-53'], ['00:15:70:9F:73:64', '-78'], 
             ['00:15:70:9F:73:66', '-75'], ['00:15:70:9E:91:62', '-55'],
             ['00:23:89:3C:BE:10', '-74'], ['00:23:89:3C:BE:11', '-78'], 
             ['00:23:89:3C:BE:12', '-78'], ['00:11:B5:FE:8B:6D', '-80'], 
             ['00:15:70:9E:6C:6C', '-65'], ['00:15:70:9E:6C:6D', '-70'],
             ['00:15:70:9E:6C:6E', '-70'], ['00:15:70:9F:76:E0', '-81'], 
             ['00:15:70:9F:7D:88', '-76'], ['00:15:70:9F:73:65', '-76'], 
             ['00:23:89:3C:BD:32', '-75'], ['00:23:89:3C:BD:30', '-78'],
             ['02:1F:3B:00:01:52', '-76'] ]
}
icon_encrypton = '/kml/encrypton.png'
icon_encryptoff = '/kml/encryptoff.png'
icon_other = '/kml/reddot.png'
dict_encrypt_icon = { 'on': [ '"encrypton"',  icon_encrypton ],
                     'off': [ '"encryptoff"', icon_encryptoff],
                   'other': [ '"reddot"',     icon_other] }
