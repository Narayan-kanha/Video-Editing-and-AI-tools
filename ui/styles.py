# ui/styles.py

ADOBE_STYLESHEET = """
QMainWindow {
    background-color: #1d1d1d;
}
/* DOCK SYSTEM */
QDockWidget {
    border: 1px solid #000;
    titlebar-close-icon: url(none);
    titlebar-normal-icon: url(none);
}
QDockWidget::title {
    background: #2d2d2d;
    padding-left: 8px;
    padding-top: 4px;
    padding-bottom: 4px;
    color: #bbb;
    font-weight: bold;
    font-size: 11px;
    font-family: 'Segoe UI';
    border-bottom: 1px solid #000;
}

/* COMMON ELEMENTS */
QWidget { color: #bbb; font-size: 12px; }

QPushButton.transport {
    background-color: transparent;
    border: none;
    color: #ddd;
    font-size: 16px;
    font-weight: bold;
}
QPushButton.transport:hover { color: #3997f3; }

QSlider::groove:horizontal {
    height: 4px;
    background: #333;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3997f3;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}

/* PANEL SPECIFIC */
QFrame#TransportBar { background-color: #1d1d1d; border-top: 1px solid #111; min-height: 35px; }
QFrame#TimelineHeader { background-color: #2b2b2b; border-right: 1px solid #444; }
QFrame#TrackControl { background-color: #262626; border-bottom: 1px solid #1a1a1a; min-height: 50px; }

QTreeWidget { 
    background-color: #1e1e1e; 
    border: none; 
    color: #ccc; 
    font-size: 11px; 
}
QHeaderView::section { 
    background-color: #2a2a2a; 
    color: #aaa; 
    border: none; 
    border-right: 1px solid #111; 
    padding: 4px; 
}
"""