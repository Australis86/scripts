#!/usr/bin/env python
#-------------------------------------------------------------------------------
# Name:        ancestryged
# Purpose:     Retrieve the media files referenced by an Ancestry GEDCOM file
#              and modify the GEDCOM to use a local reference instead.
#
# Author:      Joshua White
#
# Created:     26/01/2016
# Copyright:   (c) Joshua White 2016
# Licence:     GNU Lesser GPL v3
#-------------------------------------------------------------------------------

from optparse import OptionParser
import os
import sys
import requests

def initOptions():
	'''System argument processing.'''
	global opts

	usage = "usage: %prog [options]"
	parser = OptionParser(usage=usage)

	parser.add_option("-u", "--username",
					  dest="username", default=None,
					  help="Ancestry account username")
	parser.add_option("-p", "--password",
					  dest="password", default=None,
					  help="Ancestry account password")
	parser.add_option("-g", "--gedcom",
					  dest="gedcom", default=None,
					  help="Ancestry GEDCOM file to parse")

	(opts, args) = parser.parse_args()
	return opts, args
	
	
def ancestryAuth(username, password):
	'''Connect to Ancestry and return a requests session.'''
	
	sys.stdout.write("Authenticating with Ancestry.com.au... ")
	sys.stdout.flush()
	
	# Create a requests session
	s = requests.Session()
	
	# Account details
	payload = {
		'username': username,
		'password': password
	}
	
	# Login
	s.post('https://secure.ancestry.com.au/login?ti.si=0&ti=5544&returnUrl=http://www.Ancestry.com.au', data=payload)

	# Test
	response = s.get('http://www.ancestry.com.au')

	sys.stdout.write("done.\r\n")
	sys.stdout.flush()
	
	return s
	
	
def downloadResource(session, url, fname):
	'''Download a resource from Ancestry.'''
	
	try: 
		if os.path.exists(fname) and os.path.getsize(fname) > 0:
			print "%s already exists; skipping." % fname

		else:
			r = session.get(url, stream=True)
			r.raise_for_status() # Raise an exception if not response 200
			
			with open(fname, 'wb') as f:
				for chunk in r.iter_content(chunk_size=1024): 
					if chunk: # filter out keep-alive new chunks
						f.write(chunk)
						
			print "%s successfully downloaded." % fname
		
		return True

	except Exception, err:
		print "Failed to download %s; removing incomplete file." % url
		print str(err)
		if os.path.exists(fname):
			os.remove(fname)
		return False
	
	
def fetchGEDCOM(filename):
	'''Check for the existence of the GEDCOM file and return the contents if it exists.'''
	
	if os.path.exists(filename):
		f = open(filename, 'r')
		gedcontents = f.readlines()
		f.close()
		
		return gedcontents
		
	else:
		print "GEDCOM file %s does not exist." % filename
		sys.exit(1)


def fetchResources(gedcontents, gedfile, session):
	'''Iterate through each line of the GEDCOM data and retrieve citations and media.'''
	
	# Create a folder for the new GEDCOM and output media
	gedname = os.path.basename(gedfile)
	(geddir, gedext) = os.path.splitext(gedname)
	
	if not os.path.exists(geddir):
		os.mkdir(geddir)
	
	# Create the output file
	f = open(os.path.join(geddir, gedfile), 'w')
	
	for x in xrange(0, len(gedcontents)):
		row = gedcontents[x]
		rowtype = row[2:6]
		if rowtype == 'FILE':
			# Extract the file reference
			fileref = row[7:].strip()
			
			# Check that it's an Ancestry reference
			if 'http://trees.ancestry.com' in fileref:
			
				# Extract the URL parameters
				params = fileref.split('?')
				args = params[1].split('&')
				fdata = {
					'ftype': gedcontents[x+1][7:].strip(),
					'fname': gedcontents[x+2][7:].strip().replace('/', '_') # Remove unsafe characters
				}
				
				for a in args:
					adata = a.split('=')
					fdata[adata[0]] = adata[1]
				
				# Build the new URL
				if fdata['f'] == 'image':
					mediaURL = 'http://mediasvc.ancestry.com/v2/image/namespaces/1093/media/%(guid)s.%(ftype)s?client=Trees' % fdata
					imagefile = os.path.join(geddir, '%(guid)s - %(fname)s.%(ftype)s' % fdata)
					
					# Try to download the image
					if downloadResource(session, mediaURL, imagefile):
						row = row.replace(fileref, imagefile)
					#else:
					#	row = row.replace(fileref, mediaURL)

				elif fdata['f'] == 'document':
					if fdata['ftype'] != 'htm':
						mediaURL = 'http://mediasvc.ancestry.com/v2/image/namespaces/1093/media/%(guid)s.%(ftype)s?client=Trees&filename=%(fname)s' % fdata
						docfile = os.path.join(geddir, '%(guid)s - %(fname)s.%(ftype)s' % fdata)
						
						# Try to download the image
						if downloadResource(session, mediaURL, docfile):
							row = row.replace(fileref, docfile)
						else:
							row = row.replace(fileref, mediaURL)
				
		elif rowtype == 'NOTE':
			# Accessible Ancestry citations
			noteref = row[7:].strip()
			
			# Check that it's an Ancestry reference
			if 'http://search.Ancestry.com.au' in noteref:
				# Extract the URL parameters
				params = noteref.split('?')
				args = params[1].split('&')
				ndata = {}
				
				for a in args:
					adata = a.split('=')
					ndata[adata[0]] = adata[1]

				# Build the new URL
				noteURL = 'http://search.ancestry.com.au/search/collections/%(db)s/%(h)s/printer-friendly?ti=%(ti)s&gss=%(gss)s' % ndata
				notefile = os.path.join(geddir, '%(db)s_%(h)s.htm' % ndata)

				# Try to download the citation
				if downloadResource(session, noteURL, notefile):
					row = row.replace(noteref, notefile)
				else:
					row = row.replace(noteref, noteURL)
				
		f.write(row)

		
def parseGEDCOM(gedcom, username, password):
	'''Main function to parse the GEDCOM and retrieve data from Ancestry.'''
	
	# Open the GEDCOM file
	g = fetchGEDCOM(gedcom)
	
	# Connect to Ancestry
	session = ancestryAuth(opts.username, opts.password)
	#session = None

	# Parse each line of the GEDCOM file and retrieve resources
	fetchResources(g, gedcom, session)

	
if __name__ == '__main__':
	(opts, args) = initOptions()
	
	if opts.username and opts.password and opts.gedcom:
		parseGEDCOM(opts.gedcom, opts.username, opts.password)
