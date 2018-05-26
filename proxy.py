import socket
import os
import re
import time
from thread import *

port = 12345
buffer_size = 1024*1024

# Create TCP socket
pAsServerSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

# Re-use the socket
pAsServerSocket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

# bind
pAsServerSocket.bind(("", port))
pAsServerSocket.listen(70)

def retrieve_from_server(conn, request, file_name, port_no, host_name):
	try:
		fobj1 = open("files_stored","a+")
		stored_list = fobj1.readlines()
		print "stored_list: ", stored_list, "file_name: ", file_name
		stored_list = [line.strip("\n") for line in stored_list if line.strip() != '']
		fobj1.close()
		fobj1 = open("files_stored","w")
		try:
			stored_list.remove(file_name)
			os.remove(("."+file_name).strip("\n"))
		except:
			print "file not present in server" 
		stored_list.append(file_name)
		
		print "FILES in cache are :", stored_list
		stored_list = [line for line in stored_list if line.strip() != '']
		fobj = open("." + file_name, "w")               # Sending ./ + filename
		pAsClientSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   
		pAsClientSocket.connect((host_name, port_no))
		pAsClientSocket.sendall(request)
		no_cache = 0            # means assume cache is present for that file
		file_not_found = 0      # means assume file is found in the server
		while 1:
			# receive data from web server
			data = pAsClientSocket.recv(buffer_size)
			cache_control_list = data.split("\n")
			# Detect of cache-control is no-cache
			for line in cache_control_list:
				liner = line.split()
				if (len(liner)>=2 and liner[0] == "Cache-control:" and liner[1] == "no-cache"):
					no_cache = 1
				if (len(liner)>=2 and liner[0] == "HTTP/1.0" and liner[1] == "404"):
					file_not_found = 1

			fobj.write(data)
			if (len(data) > 0):
				conn.send(data) # send to browser/client
			else:
				if no_cache == 1 or file_not_found == 1:
					os.remove("."+file_name.strip("\n"))
					stored_list.remove(file_name)
				if len(stored_list) > 3:
					print "File to be removed from cache", stored_list[0]
					os.remove(("."+stored_list[0]).strip("\n"))
					stored_list.remove(stored_list[0])
				fobj.close()
				fobj1.write("\n".join(stored_list))
				fobj1.close()
				conn.close()
				break
	except:
		print "error connecting to the server"

def conn_string(conn, clientAddr, request):
	url = request.split()[1]
	print "url is ",url

	host_name = url.replace("www.","",1)
	port_no = -1

	http_pos = host_name.find("://") # find pos of ://
	if (http_pos != -1):
		host_name = host_name[(http_pos+3):] # get the rest of url

	port_pos = host_name.find(":") # find the port pos (if any)

	# find end of web server
	first_slash = host_name.find("/")
	file_name = ''

	# getting the path for the url
	file_name = host_name[first_slash+1:]
	file_name = "/" + file_name
	words = request.split(" ")
	words[1] = file_name
	request = " ".join(words)
	###############################

	if first_slash == -1:
		first_slash = len(host_name)
	
	if (port_pos==-1 or first_slash < port_pos): 
		# default port 
		port_no = 80 
		host_name = host_name[:first_slash] 

	else: # specific port 
		port_no = int(host_name[(port_pos+1):(port_pos+1+(first_slash-port_pos-1))])
		host_name = host_name[:port_pos]

	print host_name, port_no
	check_cache(conn, file_name, host_name, port_no, request)

def check_cache(conn, file_name, host_name, port_no, request):
	# File already present in cache 
	if os.path.isfile(file_name[1:]):
		print "File present in cache"
		try:
			pAsClientMSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)   
			pAsClientMSocket.connect(('', port_no)) 
			# Get the data, time of file
			prevdate = time.ctime(os.path.getmtime("."+file_name))
			request_list = request.split("\n")

			# Adding the If-Modified-Since header
			for i in range(len(request_list)):
				if request_list[i] == "\r" or request_list[i] == "":
					continue
				if request_list[i].split()[0] == 'Host:':
					modified_header = "If-Modified-Since: " + prevdate
					modified_header = modified_header.strip("\n")
					tmplist = modified_header.split()
					tmp = tmplist[0] + " " + tmplist[1] + " " + tmplist[2] + " " + tmplist[3] + " " + tmplist[4] + " GMT " + tmplist[5]
					modified_header = tmp
					request_list.insert(i+1, modified_header)
			request = "\n".join(request_list)

			# Send conditional get to main server
			pAsClientMSocket.sendall(request)
			data = pAsClientMSocket.recv(buffer_size)
			#print "data is ", data  

			# File no modified in the server side, then retrieve the file from the cache
			if data.split()[1] == "304":
				print "Sending file from cache"
				fobj = open("." + file_name, "r")
				line_list = fobj.readlines()
				for line in line_list:
					conn.send(line)
				conn.close()
				print "File sent"
					
			# File modified in the server, get the file from the server
			else:
				print "File modifed ... Retrieving file from server"
				retrieve_from_server(conn, request, file_name, port_no, host_name)
		except:
			print "Error connecting to server"
	else:   
		# If file not present in cache retrieve it from server
		print "File not present in Cache ... Getting file from server"
		retrieve_from_server(conn, request, file_name, port_no, host_name)

while True:
	print "*****************************Proxy Server Ready*************************************\n"
	conn, clientAddr = pAsServerSocket.accept()
	print "Client address is ", clientAddr

	# get the request from browser
	request = conn.recv(buffer_size)

	# Get url of the website requested
	print "request is ", request
	start_new_thread(conn_string, (conn, clientAddr, request))
