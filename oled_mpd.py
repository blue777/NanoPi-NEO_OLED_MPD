#!/usr/bin/env python
# -*- encoding:utf8 -*-
#
#	apt-get install fonts-takao-pgothic
#	apt-get install python-mutagen python3-mutagen

import os
import sys
import time
import signal
import socket
import subprocess
import smbus
import math
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


mpd_music_dir	= "/media/"
title_height	= 18
scroll_unit		= 3

oled_width		= 128
oled_height		=  64
cover_size		= oled_height - title_height - 2

# SSD1306 --> 0
# SH1106  --> 2
oled_offset_x	= 0

font_title		= ImageFont.truetype('TakaoPGothic.ttf', int(title_height*11/12), encoding='unic')
#font_title		= ImageFont.truetype('aqua_pfont.ttf', title_height, encoding='unic')
#font_title		= ImageFont.truetype('MEIRYOB.TTC', int(title_height*10/12), encoding='unic')

font_info		= ImageFont.truetype('TakaoPGothic.ttf', 14, encoding='unic')
#font_info		= ImageFont.truetype('aqua_pfont.ttf', 16, encoding='unic')
#font_info		= ImageFont.truetype('MEIRYO.TTC', 14, encoding='unic')

font_audio		= ImageFont.load_default()

font_time		= ImageFont.truetype('TakaoPGothic.ttf', 28);
#font_time		= ImageFont.truetype('aqua_pfont.ttf', 32);
font_date		= ImageFont.truetype('TakaoPGothic.ttf', 16);
#font_date		= ImageFont.truetype('aqua_pfont.ttf', 18);


mpd_host		= 'localhost'
mpd_port		= 6600
mpd_bufsize		= 8192




def receive_signal(signum, stack):

	soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	soc.connect((mpd_host, mpd_port))
	soc.recv(mpd_bufsize)
	
	if signum == signal.SIGUSR1:
		print 'K1 pressed'
		soc.send('previous\n')
		soc.recv(mpd_bufsize)
	
	if signum == signal.SIGUSR2:
		print 'K2 pressed'
		soc.send('status\n')
		buff        = soc.recv(mpd_bufsize)
		state_list  = buff.splitlines()
		for line in range(0,len(state_list)):
			if state_list[line].startswith(r"state: "):
				info_state      = state_list[line].replace(r"state: ", "")
				print(info_state)
				if info_state == 'play' :
					soc.send('stop\n')
					soc.recv(mpd_bufsize)
				else:
					soc.send('play\n')
					soc.recv(mpd_bufsize)

	if signum == signal.SIGALRM:
		print 'K3 pressed'
		soc.send('next\n')
		soc.recv(mpd_bufsize)


signal.signal(signal.SIGUSR1, receive_signal)
signal.signal(signal.SIGUSR2, receive_signal)
signal.signal(signal.SIGALRM, receive_signal)


bus = smbus.SMBus(0)
OLED_address     = 0x3c
OLED_CommandMode = 0x00
OLED_DataMode    = 0x40


def oled_init():

	cmd	= []

	cmd	+= [0xAE]	#display off

	cmd	+= [0x40]	#set display start line

	cmd	+= [0x81]	# Contrast
	cmd	+= [0x80]	# 0 - 255, default=0x80
	
	cmd	+= [0xA1]	#set segment remap

	cmd	+= [0xA6]	#normal / reverse

	cmd	+= [0xA8]	#multiplex ratio
	cmd	+= [0x3F]	#duty = 1/64

	cmd	+= [0xC8]	#Com scan direction

	cmd	+= [0xD3]	#set display offset
	cmd	+= [0x00]	
	cmd	+= [0xD5]	#set osc division
	cmd	+= [0x80]

	cmd	+= [0xD9]	#set pre-charge period
	cmd	+= [0xF1]

	cmd	+= [0xDA]	#set COM pins
	cmd	+= [0x12]

	cmd	+= [0xDB]	#set vcomh
	cmd	+= [0x40]

	cmd	+= [0x8D]	#set charge pump enable
	cmd	+= [0x14]

	cmd	+= [0x20]	#set addressing mode
	cmd	+= [0x02]	#set page addressing mode

	cmd	+= [0xAF]	#display ON

#	bus.write_i2c_block_data(OLED_address,OLED_CommandMode,cmd)

	for byte in cmd:
		try:
			bus.write_byte_data(OLED_address,OLED_CommandMode,byte)
		except IOError:
			print("IOError")
			return -1


def oled_drawImage(image):

	if image.mode != '1' and image.mode != 'L':
		raise ValueError('Image must be in mode 1.')

	imwidth, imheight = image.size
	if imwidth != oled_width or imheight != oled_height:
		raise ValueError('Image must be same dimensions as display ({0}x{1}).' \
		.format(oled_width, oled_height))

	# Grab all the pixels from the image, faster than getpixel.
	pix		= image.load()

	pages	= oled_height / 8;
	block	= oled_width / 32;

	for page in range(pages):

		addr	= [];
		addr	+= [0xB0 | page];	# Set Page Address
		addr	+= [0x10];	# Set Higher Column Address
		addr	+= [0x00 | oled_offset_x];	# Set Lower Column Address

		try:
			bus.write_i2c_block_data(OLED_address,OLED_CommandMode,addr)
		except IOError:
			print("IOError")
			return -1

		for blk in range(block):
			data=[]
			for b in range(32):
				x	= blk * 32 + b;
				y	= page * 8

				data.append(
					((pix[(x, y+0)] >> 7) << 0) | \
					((pix[(x, y+1)] >> 7) << 1) | \
					((pix[(x, y+2)] >> 7) << 2) | \
					((pix[(x, y+3)] >> 7) << 3) | \
					((pix[(x, y+4)] >> 7) << 4) | \
					((pix[(x, y+5)] >> 7) << 5) | \
					((pix[(x, y+6)] >> 7) << 6) | \
					((pix[(x, y+7)] >> 7) << 7) );

			try:
				bus.write_i2c_block_data(OLED_address,OLED_DataMode,data)
			except IOError:
				print("IOError")
				return -1


def ImageHalftoning_FloydSteinberg(image):

	shift	= 20;

	cx, cy = image.size;

	temp	= Image.new('I', (cx, cy));
	result	= Image.new('L', (cx, cy));
	
	tmp		= temp.load();
	dst		= result.load();
	
	# Setup Gamma tablw
	gamma	= [0]*256;
	for i in range(256):
		gamma[i]	= int( math.pow( i / 255.0, 2.2 ) * ((1 << shift) - 1) );
		
	# Convert to initial value
	if image.mode == 'L':
		src		= image.load();
		for y in range(cy):
			for x in range(cx):
				tmp[(x,y)]	=  gamma[ src[(x,y)] ];

	elif image.mode == 'RGB':
		src		= image.load();
		for y in range(cy):
			for x in range(cx):
				R,G,B	= src[(x,y)];
				Y		= (R * 13933 + G * 46871 + B * 4732) >> 16;	# Bt.709
				tmp[(x,y)]	=  gamma[ Y ];

	elif image.mode == 'RGBA':
		src		= image.load();
		for y in range(cy):
			for x in range(cx):
				R,G,B,A	= src[(x,y)];
				Y		= (R * 13933 + G * 46871 + B * 4732) >> 16;	# Bt.709
				tmp[(x,y)]	=  gamma[ Y ];

	else:
		raise ValueError('Image.mode is not supported.')	

	# Error diffuse
	for y in range(cy):
		for x in range(cx):
			c	= tmp[(x,y)];
			e	= c if c < (1 << shift) else (c - ((1 << shift) - 1));
			
			dst[(x,y)]	= 0 if c < (1 << shift) else 255;

			# FloydSteinberg
			#	-		*		7/16
			#	3/16	5/16	1/16
			if  (x+1) < cx :
				tmp[(x+1,y)]	+= e * 7 / 16;

			if (y+1) < cy :
				if 0 <= (x-1) :
					tmp[(x-1,y+1)]	+= e * 3 / 16;

				tmp[(x,y+1)]		+= e * 5 / 16;

				if (x+1) < cx :
					tmp[(x+1,y+1)]	+= e * 1 / 16;

	return	result;

# initialize OLED
oled_init()

# OLED images
image			= Image.new('L', (oled_width, oled_height))
draw			= ImageDraw.Draw(image)
draw.rectangle((0,0,oled_width,oled_height), outline=0, fill=0)


music_file      = ""
cover_image     = Image.new('L', (cover_size, cover_size))
title_image     = Image.new('L', (oled_width, title_height))
title_offset    = 0

# Draw opening image
try:
	oled_drawImage(Image.open('opening.png').resize((oled_width,oled_height)).convert('L'))
	time.sleep(3)
except:
	oled_drawImage(image)


# Socket 
soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
soc.connect((mpd_host, mpd_port))
soc.recv(mpd_bufsize)

soc.send('commands\n')
rcv = soc.recv(mpd_bufsize)
print("commands:")
print("----- start ----------")
print( rcv )
print("----- end ----------\n")


while True:

	soc.send('currentsong\n')
	buff        = soc.recv(mpd_bufsize)
	song_list   = buff.splitlines()

#	print("currentsong:")
#	print("----- start ----------")
#	print( buff )
#	print("----- end ----------\n")

	soc.send('status\n')
	buff        = soc.recv(mpd_bufsize)
	state_list  = buff.splitlines()

#	print("status:")
#	print("----- start ----------")
#	print( buff )
#	print("----- end ----------\n")

	info_state      = ""
	info_audio      = ""
	info_elapsed    = 0
	info_duration   = 0
	info_title      = ""
	info_artist     = ""
	info_album      = ""
	info_file       = ""

	for line in range(0,len(state_list)):
		if state_list[line].startswith("state: "):     info_state      = state_list[line].replace("state: ", "")
		if state_list[line].startswith("audio: "):     info_audio      = state_list[line].replace("audio: ", "")
		if state_list[line].startswith("elapsed: "):   info_elapsed    = float(state_list[line].replace("elapsed: ", ""))
		if state_list[line].startswith("time: "):      info_duration   = float(state_list[line].split(":")[2])

	for line in range(0,len(song_list)):
		if song_list[line].startswith("file: "):       info_file       = song_list[line].replace("file: ", "")
		if song_list[line].startswith("Artist: "):     info_artist     = song_list[line].replace("Artist: ", "")
		if song_list[line].startswith("Album: "):      info_album      = song_list[line].replace("Album: ", "")
		if song_list[line].startswith("Title: "):      info_title      = song_list[line].replace("Title: ", "")

	# clear the image
	draw.rectangle((0,0,oled_width,oled_height), outline=0, fill=0)

	if info_state != "stop":

		if info_title == "" :
			name    = info_file.split('/')
			name.reverse()
			info_title  = name[0]
	
			try:
				info_album  = name[1]
			except:
				info_album  = ""
	
			try:	
				info_artist = name[2]
			except:
				info_artist = ""

		if info_file != music_file :
	
			music_file  = info_file;
			file_path   = mpd_music_dir + info_file
			cover_path  = mpd_music_dir + os.path.split(music_file)[0] + "/front.jpg"
	
			print('--------------------------------------------')
			print(file_path)
			
			try:
			
				from mutagen import File
				file = File(file_path) # mutagen can automatically detect format and typeof tags
				
				if hasattr(file,'tags') :
		
					# for FLAC
					if hasattr(file,'pictures') :
						print( 'type = pictures' )
						print( file.pictures )
						artwork = file.pictures[0].data
		
					# for mp3
					elif 'APIC:' in file :
						print( 'type = APIC' )
						artwork = file.tags['APIC:'].data
		
					# for m4a
					elif 'covr' in file :
						print( 'type = covr' )
#                       print dir( file.tags['covr'][0])
						artwork = file.tags['covr'][0]
			
					else:
						print('NoPicture!, dump tags')
						print( file.tags )
					
					with open('front.jpg', 'wb') as img:
						img.write(artwork) # write artwork to new image
				
					cover_path  = "front.jpg"
		
				else:
					print( 'type = NO TAGS')
	
			except:
				print("Exception! :", sys.exc_info() )
				print( file.tags )
	
			print( cover_path )

			cover_draw  = ImageDraw.Draw(cover_image)
			cover_draw.rectangle((0,0,cover_size-1,cover_size-1), outline=255, fill=0)

			if os.path.isfile( cover_path ) :
				front_image = Image.open(cover_path).convert('L').resize((cover_size-2,cover_size-2),Image.ANTIALIAS)
				front_image	= ImageHalftoning_FloydSteinberg( front_image )
				cover_image.paste( front_image, (1,1)) 
			else:
				text_x, text_y = font_audio.getsize("NoImage")
				cover_draw.text(((cover_size-text_x)/2, (cover_size - text_y)/2 ), "NoImage", font=font_audio, fill=255)

			# Generate title image
			title_width, dmy_y   = font_title.getsize(unicode(info_title,'utf-8'))
			title_offset    = oled_width / 2;
			title_image     = Image.new('L', (title_width, title_height))
			title_draw      = ImageDraw.Draw(title_image)
			title_draw.rectangle((0,0, title_width, title_height), outline=0, fill=0)
			title_draw.text((0,0), unicode(info_title,'utf-8'), font=font_title, fill=255)

		# Title
		x   = 0
		y   = 0
		if oled_width < title_image.width :
			if title_image.width < -title_offset :	
				title_offset    = oled_width / 2
	
			if title_offset < 0 :
				x   = title_offset
			
			title_offset    = title_offset - scroll_unit
	
		image.paste(title_image, (x,y))
		x   = 0;
	
		# Current playback position
		y   += title_height;
		r	= (oled_width * info_elapsed / info_duration) if 0 < info_duration else oled_width
		draw.line((x, y, r, y ), fill=255)
	 
		# Cover Image
		y   += 2;
		image.paste( cover_image, (x,y)) 

		# artist name, album name, audio format
		x   = cover_size + 3;
		y	+= 1
		draw.text((x, y), unicode(info_artist,'utf-8'), font=font_info, fill=255)
		draw.text((x, y + (oled_height - 10 - 1 - y) / 2), unicode(info_album,'utf-8'), font=font_info, fill=255)
		draw.text((x, oled_height - 10), unicode(info_audio,'utf-8'), font=font_audio, fill=255)

	else:

		music_file  = ""

		draw.text((2, 2),time.strftime("%A"),		font=font_date,fill=255)
		draw.text((2,18),time.strftime("%e %b %Y"),	font=font_date,fill=255)
		draw.text((2,32),time.strftime("%X"),		font=font_time,fill=255)

	oled_drawImage(image)
#	image.save( 'oled_image.png')
	
