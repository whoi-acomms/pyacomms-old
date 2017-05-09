"""
This demo demonstrates how to embed a matplotlib (mpl) plot 
into a PyQt4 GUI application, including:

* Using the navigation toolbar
* Adding data to the plot
* Dynamically modifying the plot's properties
* Processing mpl events
* Saving the plot to a file from a menu

The main goal is to serve as a basis for developing rich PyQt GUI
applications featuring mpl plots (using the mpl OO API).

Eli Bendersky (eliben@gmail.com)
License: this code is in the public domain
Last modified: 19.01.2009
"""
import sys, os, random
from PySide.QtCore import *
from PySide.QtGui import *
from acomms import CycleStats, CycleStatsList
import magiccstbox



os.environ['QT_API'] = 'pyside'
import matplotlib
matplotlib.use('Qt4Agg')
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt4agg import NavigationToolbar2QTAgg as NavigationToolbar
from matplotlib.figure import Figure




class AppForm(QMainWindow):
    def __init__(self, cst_list, parent=None):
        QMainWindow.__init__(self, parent)
        self.setWindowTitle('Magic CST GUI')

        self.create_menu()
        self.create_main_frame()
        self.create_status_bar()

        self.textbox.setText('1 2 3 4')
        
        
        self.data = [1, 2, 3, 4]
        #self.data = [result.cst['snr_in'] for result in results_list]
        #self.data = cst_list;
        
        self.cst_list = cst_list
        self.cst_dol = cst_list.to_dict_of_lists()
        
        
        if len(cst_list) > 0:
            self.table.setColumnCount(len(cst_list[0]))
            self.table.setRowCount(len(cst_list))
            # Optional, set the labels that show on top
            self.table.setHorizontalHeaderLabels(CycleStats.fields)
        
        for row_num in range(len(cst_list)):
            for col_num in range(len(CycleStats.fields)):
                text = cst_list[row_num][CycleStats.fields[col_num]]
                table_item = QTableWidgetItem(str(text))
                self.table.setItem(row_num, col_num, table_item)

        # Also optional. Will fit the cells to its contents.
        self.table.resizeColumnsToContents()

        
 
        
        self.on_draw()
        
        

    def save_plot(self):
        file_choices = "PNG (*.png)|*.png"
        
        path = unicode(QFileDialog.getSaveFileName(self, 
                        'Save file', '', 
                        file_choices))
        if path:
            self.canvas.print_figure(path, dpi=self.dpi)
            self.statusBar().showMessage('Saved to %s' % path, 2000)
    
    def on_about(self):
        msg = """ The Magic CST GUI
        """
        QMessageBox.about(self, "About the demo", msg.strip())
    
    def on_pick(self, event):
        # The event received here is of the type
        # matplotlib.backend_bases.PickEvent
        #
        # It carries lots of information, of which we're using
        # only a small amount here.
        # 
        box_points = event.artist.get_bbox().get_points()
        msg = "You've clicked on a dot with coords:\n %s" % box_points
        
        QMessageBox.information(self, "Click!", msg)
    
    def on_draw(self):
        """ Redraws the figure
        """
        #str = unicode(self.textbox.text())
        #self.data = map(int, str.split())
        
        xdata = self.cst_dol['toa']

        # clear the axes and redraw the plot anew
        #
        
        plot_fields = []
        # Create subplots for each checked item
        for index in xrange(self.field_listbox.count()):
            item = self.field_listbox.item(index)
            ischecked = bool(item.checkState())
            if ischecked:
                plot_fields.append(item.text())
        
        if len(plot_fields) > 0:
            nrows = len(plot_fields)
            ncols = 1
            
            self.fig.clear()
            for row in xrange(nrows):
                ydata = self.cst_dol[plot_fields[row]]
                axes = self.fig.add_subplot(nrows, ncols, row)
                axes.plot(xdata, ydata, marker=".", linewidth=1)
                axes.set_ylabel(plot_fields[row])

        
        else:        
            
            # Pick the data based on the combo box value
            self.axes = self.fig.add_subplot('111')
            ydata = self.cst_dol[str(self.plot_combobox.currentText())]
            
            
            self.axes.clear()        
            self.axes.grid(self.grid_cb.isChecked())
                    
            self.axes.plot(xdata, ydata, marker=".", linewidth=self.slider.value())
        
        self.fig.autofmt_xdate()
        
        self.canvas.draw()
    
    def create_main_frame(self):
        self.main_frame = QWidget()
        
        # Create the mpl Figure and FigCanvas objects. 
        # 5x4 inches, 100 dots-per-inch
        #
        self.dpi = 100
        self.fig = Figure(dpi=self.dpi)
        self.canvas = FigureCanvas(self.fig)
        self.canvas.setParent(self.main_frame)
        
        # Since we have only one plot, we can use add_axes 
        # instead of add_subplot, but then the subplot
        # configuration tool in the navigation toolbar wouldn't
        # work.
        #
        
        
        # Bind the 'pick' event for clicking on one of the bars
        #
        self.canvas.mpl_connect('pick_event', self.on_pick)
        
        # Create the navigation toolbar, tied to the canvas
        #
        self.mpl_toolbar = NavigationToolbar(self.canvas, self.main_frame)
        
        # Other GUI controls
        # 
        self.textbox = QLineEdit()
        self.textbox.setMinimumWidth(200)
        self.connect(self.textbox, SIGNAL('editingFinished ()'), self.on_draw)
        
        self.draw_button = QPushButton("&Draw")
        self.connect(self.draw_button, SIGNAL('clicked()'), self.on_draw)
        
        self.grid_cb = QCheckBox("Show &Grid")
        self.grid_cb.setChecked(False)
        self.connect(self.grid_cb, SIGNAL('stateChanged(int)'), self.on_draw)
        
        slider_label = QLabel('Line width:')
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(1, 10)
        self.slider.setValue(2)
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TicksBothSides)
        self.connect(self.slider, SIGNAL('valueChanged(int)'), self.on_draw)
        
        self.table = QTableWidget()
        
        plot_cb_label = QLabel("Variable to plot:")
        self.plot_combobox = QComboBox()
        self.plot_combobox.addItems(CycleStats.fields)
        self.connect(self.plot_combobox, SIGNAL('currentIndexChanged(int)'), self.on_draw)
        
        self.field_listbox = QListWidget()
        self.field_listbox.setSelectionMode(QAbstractItemView.NoSelection)
        self.field_listbox.addItems(CycleStats.fields)
        for index in xrange(self.field_listbox.count()):
            item = self.field_listbox.item(index)
            item.setCheckState(Qt.CheckState(0))
        self.field_listbox.setMinimumWidth(self.field_listbox.sizeHintForColumn(0))
        self.connect(self.field_listbox, SIGNAL('itemClicked(QListWidgetItem *)'), self.on_draw)
        
        toparea = QSplitter()
        toparea.addWidget(self.field_listbox)
        toparea.addWidget(self.canvas)
        
        
        
        #
        # Layout with box sizers
        # 
        hbox = QHBoxLayout()
        
        for w in [  plot_cb_label, self.plot_combobox, self.grid_cb,
                    slider_label, self.slider]:
            hbox.addWidget(w)
            hbox.setAlignment(w, Qt.AlignVCenter)
        
        plotsection = QVBoxLayout()
        plotsection.addWidget(self.mpl_toolbar)
        plotsection.addWidget(toparea)
        #plotsection.addLayout(hbox)
        plotsectionwidget = QWidget()
        plotsectionwidget.setLayout(plotsection)
        
        vbox = QSplitter(Qt.Orientation.Vertical)
        vbox.addWidget(plotsectionwidget)
        vbox.addWidget(self.table)
        
        bigbox = QVBoxLayout()
        bigbox.addWidget(vbox)
        
        self.main_frame.setLayout(bigbox)
        self.setCentralWidget(self.main_frame)
    
    def create_status_bar(self):
        self.status_text = QLabel("Loaded CSTs")
        self.statusBar().addWidget(self.status_text, 1)
        
    def create_menu(self):        
        self.file_menu = self.menuBar().addMenu("&File")
        
        load_file_action = self.create_action("&Save plot",
            shortcut="Ctrl+S", slot=self.save_plot, 
            tip="Save the plot")
        quit_action = self.create_action("&Quit", slot=self.close, 
            shortcut="Ctrl+Q", tip="Close the application")
        
        self.add_actions(self.file_menu, 
            (load_file_action, None, quit_action))
        
        self.help_menu = self.menuBar().addMenu("&Help")
        about_action = self.create_action("&About", 
            shortcut='F1', slot=self.on_about, 
            tip='About the demo')
        
        self.add_actions(self.help_menu, (about_action,))

    def add_actions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def create_action(  self, text, slot=None, shortcut=None, 
                        icon=None, tip=None, checkable=False, 
                        signal="triggered()"):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":/%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action

def plot_csts(cst_list):
    app = QApplication(sys.argv)
    form = AppForm(cst_list)
    form.show()
    app.exec_()    


def main():
    app = QApplication(sys.argv)
    form = AppForm(None)
    form.show()
    app.exec_()


if __name__ == "__main__":
    main()