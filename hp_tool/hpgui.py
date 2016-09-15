from Tkinter import *
import ttk
import tkFileDialog
import tkMessageBox
import tkSimpleDialog
import os
import sys
import datetime
import re
from hp_data import *


class HPGUI(Frame):

    def load_input(self):
        d = tkFileDialog.askdirectory()
        self.inputdir.delete(0, 'end')
        self.inputdir.insert(0, d)

    def load_output(self):
        d = tkFileDialog.askdirectory()
        self.outputdir.delete(0, 'end')
        self.outputdir.insert(0, d)

    def select_metadatafile(self):
        f = tkFileDialog.askopenfilename()
        self.metadatafilename.delete(0, 'end')
        self.metadatafilename.insert(0,f)

    def select_preferencesfile(self):
        f = tkFileDialog.askopenfilename()
        self.prefsfilename.delete(0, 'end')
        self.prefsfilename.insert(0,f)

    def preview_filename(self):
        prefs = parse_prefs(self.prefsfilename.get())
        testNameStr = datetime.datetime.now().strftime('%Y%m%d')[2:] + '-' + \
                    prefs['organization'] + prefs['username'] + '-' + prefs['seq']
        if self.additionalinfo.get():
            testNameStr += '-' + self.additionalinfo.get()
        tkMessageBox.showinfo('Filename Preview', testNameStr)

    def select_keywords(self):
        category1 = []
        category2 = []
        category3 = []
        hierarchy = {}
        with open('Foundation List 2.0.1.txt', 'rb') as f:
            for line in f:
                line = line.strip()
                if line.startswith('[~') and line.isupper():
                    data = line.translate(None, '[]~{}').strip() # strip off non-alphabetic characters
                    category1.append(data)
                    hierarchy[data] = {}
                    currentLevel = data
                elif line.startswith('[~'):
                    data = line.translate(None, '[]~{}').strip()
                    category2.append(data)
                    hierarchy[currentLevel][data] = []
                    currentSublevel = hierarchy[currentLevel][data]
                else:
                    data = line.translate(None, '[]~{}').strip()
                    category3.append(data)
                    currentSublevel.append(data)


        top = Toplevel(self)
        selections = None

        top.title("About this application...")

        self.cat1val = StringVar()
        self.cat1 = ttk.Combobox(top, textvariable=self.cat1val)
        self.cat1['values'] = tuple(hierarchy.keys())
        self.cat1.current(0)
        self.cat1.grid(ipadx=5, ipady=5, padx=5, pady=5)

        self.cat2val = StringVar()
        self.cat2 = ttk.Combobox(top, textvariable=self.cat2val)
        self.cat2['values'] = tuple(hierarchy[self.cat1val].keys())
        self.cat2.bind('<<ComboboxSelected>>', self.getComboboxUpdate)
        self.cat2.current(0)
        self.cat2.grid(row=1, column=0, ipadx=5, ipady=5, padx=5, pady=5)

        button = Button(top, text="Dismiss", command=top.destroy)
        button.grid(row=1)

        return selections

    def go(self):
        shortFields = ['collReq', 'camera', 'localcam', 'lens', 'locallens', 'hd', 'sspeed', 'fnum', 'expcomp', 'iso',
                       'noisered', 'whitebal', 'expmode', 'flash', 'focusMode', 'kvalue', 'location', 'obfilter',
                       'obfiltertype', 'lensfilter']
        kwargs = {'preferences':self.prefsfilename.get(),
                  'metadata':self.metadatafilename.get(),
                  'imgdir':self.inputdir.get(),
                  'outputdir':self.outputdir.get(),
                  'recursive':self.recBool.get(),
                  'xdata':self.xdata.get().split(','),
                  'keywords':self.keywords.get().split(','),
                  'additionalInfo':self.additionalinfo.get(),
                  }
        for fieldNum in xrange(len(shortFields)):
            try:
                kwargs[shortFields[fieldNum]] = self.attributes[self.descriptionFields[fieldNum]].get()
            except AttributeError:
                kwargs[shortFields[fieldNum]] = str(self.filterBool.get())

        process(**kwargs)

    def createWidgets(self):
        self.recBool = BooleanVar()
        self.recBool.set(False)
        self.inputSelector = Button(self, text='Input directory: ', command=self.load_input, width=20)
        self.inputSelector.grid(row=0,column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.recbox = Checkbutton(self, text='Include subdirectories', variable=self.recBool)
        self.recbox.grid(row=0, column=3, ipadx=5, ipady=5, padx=5, pady=5)
        self.inputdir = Entry(self)
        self.inputdir.insert(END, os.getcwd())
        self.inputdir.grid(row=0, column=1, ipadx=5, ipady=5, padx=0, pady=5, columnspan=2)

        self.outputSelector = Button(self, text='Output directory: ', command=self.load_output, width=20)
        self.outputSelector.grid(row=1, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=1)
        self.outputdir = Entry(self, width=20)
        self.outputdir.insert(END, os.getcwd())
        self.outputdir.grid(row=1, column=1, ipadx=2, ipady=5, padx=5, pady=5, columnspan=2)

        self.metadatalabel = Button(self, text='Metadata file: ', command=self.select_metadatafile, width=20)
        self.metadatalabel.grid(row=0, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.metadatafilename = Entry(self, width=20)
        self.metadatafilename.insert(END, os.path.join(os.getcwd(), 'metadata.txt'))
        self.metadatafilename.grid(row=0, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.prefsbutton = Button(self, text='Preferences file: ', command=self.select_preferencesfile, width=20)
        self.prefsbutton.grid(row=1, column=4, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)
        self.prefsfilename = Entry(self, width=20)
        self.prefsfilename.insert(END, os.path.join(os.getcwd(), 'preferences.txt'))
        self.prefsfilename.grid(row=1, column=6, ipadx=5, ipady=5, padx=5, pady=5, columnspan=2)

        self.additionallabel = Label(self, text='Additional Text to add at end of new filenames: ')
        self.additionallabel.grid(row=2, column=0, ipadx=5, ipady=5, padx=5, pady=5, columnspan=3)
        self.additionalinfo = Entry(self, width=10)
        self.additionalinfo.grid(row=2, column=3, ipadx=5, ipady=5, padx=5, pady=5, sticky='W')

        self.previewbutton = Button(self, text='Preview filename', command=self.preview_filename, bg='cyan')
        self.previewbutton.grid(row=2, column=4)

        self.sep1 = ttk.Separator(self, orient=HORIZONTAL).grid(row=3, columnspan=8, sticky='EW')

        self.keywordsbutton = Button(self, text='Choose Keywords...', command=self.select_keywords)
        self.keywordsbutton.grid(row=4, column=1, ipadx=5, ipady=5, padx=5, pady=5, sticky='E')
        # self.keywordslabel = Label(self, text='Keywords: ')
        # self.keywordslabel.grid(row=4, column=1, ipadx=5, ipady=5, padx=5, pady=5, sticky='E')
        self.keywords = Entry(self, width=10)
        self.keywords.grid(row=4, column=2, ipadx=5, ipady=5, padx=5, pady=5)


        self.xdatalabel = Label(self, text='ExtraData: ')
        self.xdatalabel.grid(row=4, column=3, ipadx=5, ipady=5, padx=5, pady=5, sticky='E')
        self.xdata = Entry(self, width=10)
        self.xdata.grid(row=4, column=4, ipadx=5, ipady=5, padx=5, pady=5, sticky='W')

        self.sep2 = ttk.Separator(self, orient=HORIZONTAL).grid(row=5, columnspan=8, sticky='EW')

        self.descriptionFields = ['Coll. Request ID', 'Camera Serial #*', 'Local ID', 'Lens Serial #*', 'Local Lens ID', 'Hard Drive Location',
                                  'Shutter Speed*', 'F-Number*', 'Exposure Compensation*', 'ISO*', 'Noise Reduction*', 'White Balance*',
                                  'Color Temp (K)', 'Exposure Mode*', 'Flash Setting*', 'Focus Mode*', 'Location', 'On-board Filter',
                                  'OB Filter Type', 'Lens Filter Type']

        self.descriptionlabel = Label(self, text = 'Enter camera information. A * indicates the program will attempt '
                                                   'pull that field from image Exif data if left blank.')
        self.descriptionlabel.grid(row=6,columnspan=8, sticky='W')
        row = 7
        col = 0
        self.attributes = {}
        for field in self.descriptionFields:
            self.attrlabel = Label(self, text=field).grid(row=row, column=col, ipadx=5, ipady=5, padx=5, pady=5, sticky='W' )
            self.attributes[field] = Entry(self, width=10)
            self.attributes[field].grid(row=row, column=col+1, ipadx=0, ipady=5, padx=5, pady=5, sticky='W')
            col += 2
            if col == 8:
                row += 1
                col = 0

        obfilterLoc = self.attributes['On-board Filter'].grid_info()
        self.attributes['On-board Filter'].grid_forget()
        self.filterBool = BooleanVar()
        self.filterBool.set(False)
        self.attributes['On-board Filter'] = Radiobutton(self, text='T', variable=self.filterBool, value=True)
        self.attributes['On-board Filter'].grid(row=obfilterLoc['row'], column=obfilterLoc['column'], ipadx=5,  padx=5, sticky='N')
        self.attributes['On-board Filter'] = Radiobutton(self, text='F', variable=self.filterBool, value=False)
        self.attributes['On-board Filter'].grid(row=obfilterLoc['row'], column=obfilterLoc['column'], ipadx=5, padx=5, sticky='S')



        lastLoc = self.attributes['Lens Filter Type'].grid_info()
        lastRow = int(lastLoc['row'])
        self.sep3 = ttk.Separator(self, orient=HORIZONTAL).grid(row=lastRow+1, columnspan=8, sticky='EW')

        self.okbutton = Button(self, text='OK ', command=self.go, width=20, bg='green')
        self.okbutton.grid(row=lastRow+2,column=3, ipadx=5, ipady=5, sticky='E')

        self.cancelbutton = Button(self, text='Cancel', command=self.quit, width=20, bg='red')
        self.cancelbutton.grid(row=lastRow+2, column=4, ipadx=5, ipady=5, padx=5, sticky='W')

    def __init__(self, master=None):
        Frame.__init__(self, master)
        self.grid()
        self.createWidgets()


def main():
    root = Tk()
    root.resizable(width=False, height=False)
    app = HPGUI(master=root)
    app.mainloop()

if __name__ == '__main__':
    main()
