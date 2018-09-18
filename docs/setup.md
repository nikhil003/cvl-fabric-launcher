Configuring Strudel-desktop
===========================

Configuring strudel desktop consistes of three major activities
1. Configuring the desktop environment on the system where it will run.
2. Configuring a json file to cause that desktop environment to run
3. Storing the json file on a URL and registering that URL with the upstream maintainers to make it easy for your users.

Configuring the desktop environment
-----------------------------------

The minimum requirement here is installing a vncserver and a window manager. Personally the Monash team use either turbovnc or tigervnc server, and the MATE desktop. For CentOS 7 based systems MATE must be obtained from EPEL.

In addition to choosing a desktop environment you may want to customise your menues. The Monash team make use of a wrapper script to execute vncserver which sets environment variables like XDG_DATA_DIR and XDG_CONFIG_DIR. The configuring of desktops via the XDG standard is beyond the scope of this document.

At this point, you should make sure your environment runs and your happy with it. You should be able to manually start the vncserver, create an SSH tunnel (using the -L flag) and connect a locally running vncviewer to your server.

Configuring the json file
-------------------------

Now that you can happily start a vncserver, you need to decide on some of the policys you will enforce around people using it. Are you running a vncserver on the login nodes? Or on compute nodes via a scheduler? How much RAM can a vncserver/desktop use? Do you allow users to select the amount of RAM they want or do you offer a few predefined options?

The first thing you should do here is become comfortable with how to execute your vncserver with whatever options you want. You need to know how to

1. start the vncserver
2. find out if the vncserver is running or queued
3. obtain the host the vncserver is running on
4. obtain the port the vncserver is running on
5. obtain the password to the vncserver
6. create a tunnel to the vncserver
7. stop the vncserver.

Each of these functions consists of a command and a regular expression to extract the value in question. The regular expression gives a name to the variable that can be used in templating subsequent commands.

Once your figured out how to do each of these things manually its time to encode them into the json file. The easiest way to do this is probably to open up make_default_flavours.py and copy the function getCVLSiteConfigSlurm, change its name and start hacking. You'll also need to go down to the bottom of the file and find something like the seciont labeled with the command Generic Config, copy this and make it call your new function and write out a new json file.

Once you've executed make_default_flavours.py and have a json file in hand, you can start strudel an drop the json file onto the main window, then click login. At this point somethign will probably fail. Often its got to do with escaping the commands executed via SSH in the correct manner. You can start editing the commands entered into make_default_flavours.py till you successfully generate a json file that works.

Note that you could at this point make the decision that writing correctly escapped bash commands to the json file is a mugs game and you'd rather install a wrapper script on your login node to simplify the interface. Certainly M3 uses the wrapper script method while CVL uses the escapped bash command method. The choice is up to you.

Serving the json file
---------------------

This is actually pretty easy. You need to stick the json file on a web server somewhere so that your users can get it. You then tell the monash team the URL for that file and we stick it in the master site list. Next time a user starts Strudle the URL will show up under the file->manage sites menu and your users can check the box to say they want to use your site.
