#!/usr/bin/env python

import ntpath
import xml.etree.ElementTree as ET
import sys
import re
import os
import urllib
import argparse

parser = argparse.ArgumentParser()

parser.add_argument("mm_file", type=str,
                    help="mindmap file to be parsed")
parser.add_argument("tex_file", type=str,
                    help="latex beamer body file to be created")
parser.add_argument("-v", "--verbosity",
                    help="increase output verbosity", action="store_true")
parser.add_argument("-all", "--all",
                    help="parse all slides", action="store_true")
parser.add_argument("-nn", "--nonotes",
                    help="create no notes", action="store_true")
cmdl_args = parser.parse_args()

global_image_dir = "."
global_movie_dir = "."
global_nonotes = 'off'

def startTexEnv(env, opt=None, secarg=None):
    res = "\\begin{%s}"%env
    if opt:
        res += "[%s]"%opt
    if secarg:
        res += "{%s}"%secarg
    res += "\n"
    
    return res

def stopTexEnv(env):
    return "\\end{" + env + "}\n"

def checkRemoveCommand(node, command):
    posa = node.attrib['TEXT'].find("#"+command)
    if posa >= 0:
        posb = node.attrib['TEXT'].find("#", posa+1)
        fullcommand = node.attrib['TEXT'][posa:posb+1]
        node.attrib['TEXT'] = node.attrib['TEXT'].replace(fullcommand, "", 1)
        offset = 1
        while (any(fullcommand[offset+len(command)] in s for s in [' ', '\n'])) and (offset+len(command)+1) < len(fullcommand): 
            offset+=1
        return fullcommand[offset+len(command):-1]    
    return None

def checkRemoveMarker(node, marker):
    text = node.attrib['TEXT']
    pos = text.find(marker, 0, len(marker))
    if pos == 0:
        node.attrib['TEXT'] = node.attrib['TEXT'].replace(marker, "")
        return True
    return False

def getTexContent(node):
    
    text = node.attrib['TEXT'].encode('UTF-8')
    res = ""
    
    #output equation
    eqs = node.findall(".//hook[@EQUATION]")
    for eq in eqs:
            equation = eq.attrib['EQUATION']
            res += "\\begin{equation}\n"
            res += equation + "\n"
            res += "\\end{equation}\n"
    if eqs != []:
    	return res
            
    #output figure
    figs = node.findall(".//hook[@URI]")
    for fig in figs:
            
            figure = fig.attrib['URI']
            scale = "0.7"
            label = "none"
            
            meta_raws = node.findall("./node")
            for meta_raw in meta_raws:
            	meta = meta_raw.attrib['TEXT'].encode('UTF-8')

            	if meta.startswith("scale:"):
            		scale = meta[6:]
            	if meta.startswith("label:"):
            		label = "fig:" + meta[6:].strip()
            
            res = startTexEnv("figure") + \
	          		"\\includegraphics[width=" + scale + "\\columnwidth]{" + global_image_dir + "/" + figure + "} \n" + \
            		"\caption{" + text + "} \n" + \
            		"\label{" + label + "} \n" + \
            		stopTexEnv("figure")
            print res
    if figs != []:
    	return res
    
    #equation node
    if text.startswith("\latex"):
        equation = text[6:]
        res  = "\\begin{equation}\n"
        res += equation + "\n"
        res += "\\end{equation}\n"
        return res
    
    #center line
    cl = checkRemoveCommand(node, "CL")
    if cl != None:
        cltext = node.attrib['TEXT'].encode('UTF-8')
        res = "\\centerline{%s}"%cltext
    	return res

	#output simple text
    text = node.attrib['TEXT'].encode('UTF-8')
    res = text + "\n"
    return res


    
#####################################################################

def processSlideNodes(section_node):
	slide_nodes = section_node.findall("node")
	for slide in slide_nodes:
		print "found slide  : ", slide.attrib['TEXT'].encode('UTF-8')

		print_slide_id = False

		title = slide.attrib['TEXT'].encode('UTF-8')
		
		if print_slide_id:
			title = title + " -- \\texttt{ID\\char`_" + slide.attrib['ID'][3:] + "}"
		
		print "slide: ", title

		section = checkRemoveCommand(slide, "SEC")
		if section != None:
			of.write("\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
			of.write("\\part{"+section+"}\n")
			of.write("\\frame{\\partpage}\n")
			continue

		of.write("\n%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%\n")
		of.write(startTexEnv("frame", "fragile"))
		of.write("\\frametitle{"+title+"}\n")

		columns = False
		itemize = False
		enumerate = False
		table = False
		spacing = True

		contents = slide.findall(".node")

		for content in contents:
	
			## check for no spacing
			in_spacing = checkRemoveCommand(content, "NS")
			if in_spacing != None:
				spacing = False
	
			if table:
				spacing = False
                
			## check for table start
			table_command = checkRemoveCommand(content, "TABLE")
			if table_command != None:
				table = True
				spacing = False
				table_options = table_command.encode('UTF-8').split("|")[1]
				
				print "start table", table_options
				of.write(startTexEnv("centering"))
				of.write(startTexEnv("tabular", secarg=table_options))
                
			## check for table end
			table_command = checkRemoveCommand(content, "TE")
			if table_command != None:
				table = False
				
				print "stop table"
				of.write(stopTexEnv("tabular"))  
				of.write(stopTexEnv("centering"))  
                
			## check for itemization item
			if checkRemoveMarker(content, "* "):

				if not itemize:
					if enumerate:
						enumerate = False
						of.write(stopTexEnv("enumerate"))
				
					itemize = True
					of.write(startTexEnv("itemize"))  
		
				of.write("  \\item ")# + getTexContent(content) + "\n")

			elif itemize:
				itemize = False
				of.write(stopTexEnv("itemize"))
		
			## check for enumeration item
			resume = checkRemoveCommand(content, "RESUME")
			cont_enum = checkRemoveCommand(content, "CE")
			if checkRemoveMarker(content, "1. "):
		
				if not enumerate:
					if itemize:
						itemize = False
						of.write(stopTexEnv("itemize"))
				
					enumerate = True
					of.write(startTexEnv("enumerate"))
					if resume != None:
						of.write(r"\setcounter{enumi}{%s}"%resume)
		
				of.write("  \\item ")# + getTexContent(content) + "\n")

			elif enumerate and (cont_enum==None):
				enumerate = False
				of.write(stopTexEnv("enumerate"))

	
			figure=checkRemoveCommand(content, "FIG")
			if figure != None:
				# legacy
				fig_width=checkRemoveCommand(content, "SCALE")

				split_content = figure.encode('UTF-8').split("|")
				if len(split_content) > 0:
					fig_file = split_content[0].strip()
				else:
					fig_file = None
					return
				if len(split_content) > 1:
					fig_width = split_content[1].strip()
				else:
					fig_width = None
				if len(split_content) > 2:
					fig_height = split_content[2].strip()
				else:
					fig_height = None

				if (not fig_width) and (not fig_height): fig_width = "0.9"

				of.write("\\centerline{\\includegraphics[")
				if fig_width:
					of.write("width=" + fig_width + "\\columnwidth")
				if fig_height:
					of.write("height=" + fig_height + "\\textheight")
				of.write("]{" + global_image_dir + "/" + fig_file + "}}\n")
	
			mov=checkRemoveCommand(content, "MOV")
			if mov != None:
				split_content = mov.encode('UTF-8').split("|")
				mov_file = global_movie_dir + "/" + split_content[0].strip()
				mov_string = split_content[1].strip()
				
				mov_full_url = urllib.quote(os.path.abspath(mov_file), safe="%/:=&?~#+!$,;'@()*[]").replace("%", "\%")
	
				of.write("\\href{file:%s}{%s}"%(mov_full_url, mov_string))
	
			note=checkRemoveCommand(content, "NOTE")
			if (note != None) and (global_nonotes != 'on'):
			#if note != None:
				of.write("\\pdfnote{%s}"%note.encode('UTF-8'))
			else:
				print global_nonotes
	
			listing=checkRemoveCommand(content, "LST")
			if listing != None:
				split_content = listing.encode('UTF-8').split("|")
				
				selected_lines = ''
				if len(split_content) == 3:
					selected_lines = ', linerange={%s-%s}, firstnumber=%s'%(split_content[1], split_content[2], split_content[1])
				of.write(r"\lstinputlisting[title=%s %s]{%s}"%(ntpath.basename(split_content[0]), selected_lines, split_content[0]))
	
			code=checkRemoveCommand(content, "CODE")
			code_noline=checkRemoveCommand(content, "CODE_NOLINE")        
			if code != None:
	#            of.write(startTexEnv("lstlisting", r"frame=leftline, basicstyle=\small\ttfamily, numbers=none"))
				if code_noline==None:
					of.write(startTexEnv("lstlisting"))
				else:
					of.write(startTexEnv("lstlisting", r"numbers=none"))
				of.write(code)
				of.write(stopTexEnv("lstlisting"))            

			shell=checkRemoveCommand(content, "SHELL")
			if shell != None:
				of.write(startTexEnv("lstlisting", r"numbers=none"))
				of.write(shell)
				of.write(stopTexEnv("lstlisting"))            

			ref = checkRemoveCommand(content, "REF")
			if ref:
				ref_ystart = "1.05 \\textheight"
				ref_ywidth = "1.0 \\textheight"
				ref_xoff   = "0.025 \\textwidth"
				
				of.write("\\begin{textblock*}{%s}(%s,%s)"%(ref_ywidth, ref_xoff, ref_ystart))
				of.write("\\begin{rotate}{90}")
				of.write("{\\footnotesize " + ref.encode('UTF-8') + "}")
				of.write("\\end{rotate}")
				of.write("\\end{textblock*}")
				
			column = checkRemoveCommand(content, "SC")
			if column != None:
				if not columns:
					columns = True
					of.write(startTexEnv("columns"))
				else:
					of.write(stopTexEnv("column"))
		
				if column == "": column = "0.5"
			
				of.write("\n" + startTexEnv("column}{" + column + "\\textwidth"))
		
			column_end = checkRemoveCommand(content, "EC")
			if column_end != None:
				if columns:
					columns = False
					of.write(stopTexEnv("column"))
					of.write(stopTexEnv("columns"))
	
			vspace = checkRemoveCommand(content, "VS")
			if len(content) == 0 and spacing: vspace = "0.015"
			if vspace != None:
				if vspace == "": vspace = "0.05"
				of.write("\n\\vspace{%s\\textwidth}\n"%vspace)
	
			footline = checkRemoveCommand(content, "FL")
			if footline != None:
				of.write("\n\\vskip0pt plus 1filll \n {\\tiny " + footline.encode('UTF-8') + "}")
	
			## simple text
			#if (itemize == False and enumerate == False):
			of.write(getTexContent(content) + "\n\n")

		if itemize:
			of.write(stopTexEnv("itemize"))
	
		if enumerate:
			of.write(stopTexEnv("enumerate"))

		if columns:
			of.write(stopTexEnv("column"))
			of.write(stopTexEnv("columns"))

		of.write(stopTexEnv("frame"))


#####################################################################
#####################################################################
#####################################################################

tree = ET.parse(cmdl_args.mm_file)
root = tree.getroot()

of = open(cmdl_args.tex_file, 'w')

nodes = root.findall("*/node")
slides = []

global_author = 'no author name'
global_title = 'no title'
global_date = 'today'
global_type = 'lecture'
global_showall = 'off'

print "-- reading global attributes"
for att_nodes in root.findall("./node/attribute"):
    if att_nodes.attrib['NAME'] == 'author': global_author = att_nodes.attrib['VALUE']
    if att_nodes.attrib['NAME'] == 'title': global_title = att_nodes.attrib['VALUE']
    if att_nodes.attrib['NAME'] == 'date': global_date = att_nodes.attrib['VALUE']
    if att_nodes.attrib['NAME'] == 'type': global_type = att_nodes.attrib['VALUE']
    if att_nodes.attrib['NAME'] == 'showall': global_showall = att_nodes.attrib['VALUE']
    if att_nodes.attrib['NAME'] == 'imagedir': global_image_dir = att_nodes.attrib['VALUE']	
    if att_nodes.attrib['NAME'] == 'moviedir': global_movie_dir = att_nodes.attrib['VALUE']	

if cmdl_args.all:
    global_showall = 'on'
if cmdl_args.nonotes:
    global_nonotes = 'on'

print " - author  : ", global_author
print " - title   : ", global_title
print " - date    : ", global_date
print " - type    : ", global_type
print " - shwoall : ", global_showall
print " - no notes: ", global_nonotes

if (global_type != 'talk'):
	for chapter_node in nodes:
		print "found chapter: ", chapter_node.attrib['TEXT']
		
		show_chapter = False
		global_image_dir = "."
		global_movie_dir = "."
		
		for att_node in chapter_node.findall("./attribute"):
			if (att_node.attrib['NAME'] == 'show' and att_node.attrib['VALUE'] == 'on') or (global_showall == 'on') :
				show_chapter = True
			if att_node.attrib['NAME'] == 'imagedir':
				global_image_dir = att_node.attrib['VALUE']
			if att_node.attrib['NAME'] == 'moviedir':
				global_movie_dir = att_node.attrib['VALUE']
			

		if show_chapter:
			of.write("\\section{%s}\n"%chapter_node.attrib['TEXT'].encode('UTF-8'))

			#of.write("\\frame{\\tableofcontents[sectionstyle=show/show,subsectionstyle=show/show/hide]}\n")	
			of.write("\\frame{\\tableofcontents[sectionstyle=show/hide,subsectionstyle=show/show/hide]}\n")
	
			section_nodes = chapter_node.findall("node")
			for section_node in section_nodes:
		
				print "found section: ", section_node.attrib['TEXT'].encode('UTF-8')
		
				of.write("\\subsection{%s}\n"%section_node.attrib['TEXT'].encode('UTF-8'))
				of.write("\\frame{\\tableofcontents[sectionstyle=show/hide,subsectionstyle=show/shaded/hide]}\n")

				processSlideNodes(section_node)
		else:
			print "NOT SHOWING chapter %s"%chapter_node.attrib['TEXT']
else:

	processSlideNodes(root.findall(".")[0][0])

of.close()
