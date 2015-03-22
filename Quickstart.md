# Introduction #

Offline & Online operations


# Offline #

**1) fingerprints calibration.**<br>
<pre><code> ./tool/bt-dev-con &amp;&amp; xgps &amp;<br>
 ./run -n &lt;start_spid&gt; -r &lt;repeat_times&gt;<br>
 ./offline.py -c dat/&lt;time-spid&gt;.rmp<br>
 ./offline.py -u 1<br>
</code></pre>

<b>2) Dumbtest for stability.</b><br>
<pre><code>./run -d<br>
</code></pre>
<br>
<b>3) Compile all \<filename\>.py to \<filename\>.pyc.</b><br>
<pre><code>./run -m<br>
</code></pre>

<h1>Online</h1>

<b>1) Pure fingerprinting.</b><br><b><pre><code>sudo ./online.py -v<br>
</code></pre></b><br>
<b>2) Accuracy evaluation(GPS available).</b><br><b><pre><code>sudo ./test.py -v<br>
</code></pre></b>


<h1>SP id assignment</h1>
<hr />
borq: floor 8: 1-12<br>
floor 1-8: 100-899<br>
dacheng floor 12: 1200-1299, e.g. 1203:door1203.<br>
home yjl: 90-99<br>
home neighborhood: 30-89