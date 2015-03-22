**Source code update terminated because of weird problem of google code hg or sth else.**

WLAN fingerprinting and triangulation based location determination system.

1.Location fingerprinting technique observes the operating environment and estimates mobile unit's current location from these observations. It's also known as a scene analysis or pattern matching technique. This technique works under the basic assumption that every physical location has a unique characteristic or fingerprint in wireless signal space, as analogy to every human being has a unique fingerprint. The operating procedure of this technique mainly consists of offline sampling(aka calibration) and online locationing(also operational) phases:
> (1) Offline phase includes raw data filtering and collection based on GPS listening and WLAN scanning(or sniffing), and followed by radio map construction from the just collected raw material. The format or the scheme of radio map mainly depends on corresponding online location determination scheme for fulfilling the different level of performance requirements. e.g. mean, mean/var,histogram, etc.

> (2) Online phase mainly determines the location of WLAN mobile unit based on the real-time WLAN measurements and the useful information from radio map database. The detailed implementation depends heavily on the scheme used in the phase, such as deterministic and probablistic approaches.

2.Location triangulation includes the determinatin of the location of base station and the relative distance between base station and the mobile unit. The distance is usually solved by using the model of path attenuation for wireless signal propagation, which is often referred to as RSS based methods, together with time, phase based methods.