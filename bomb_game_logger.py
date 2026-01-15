import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import sqlite3
from datetime import datetime, timedelta
import json
import csv
import os
from collections import defaultdict
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import seaborn as sns
from PIL import Image, ImageTk

class GameResultLogger:
    def __init__(self, root):
        self.root = root
        self.root.title("Bomb Game Result Logger & Analyzer")
        self.root.geometry("1400x900")
        
        # Set style
        sns.set_style("whitegrid")
        
        # Database setup
        self.db_path = 'bomb_game_results.db'
        self.init_database()
        
        # Game constants
        self.MULTIPLIERS = [1.18, 1.49, 1.9, 2.46, 3.23, 4.31, 5.7, 7.89, 11.19, 16.01,
                            24.01, 37.36, 60.37, 92, 168, 337, 664, 2000, 2000, 2000]
        
        # Current session
        self.current_session = datetime.now().strftime("session_%Y%m%d_%H%M%S")
        self.current_balance = 1.34
        
        # Colors for UI
        self.colors = {
            'win': '#2ecc71',
            'loss': '#e74c3c',
            'primary': '#3498db',
            'secondary': '#2c3e50',
            'background': '#ecf0f1',
            'text': '#2c3e50'
        }
        
        # Create GUI
        self.create_widgets()
        self.load_initial_data()
        
        # Center window
        self.center_window()
    
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def init_database(self):
        """Initialize SQLite database with advanced analytics"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main game results table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS game_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT,
            round_number INTEGER,
            bet_amount REAL,
            strategy TEXT,
            result TEXT,
            safe_picks INTEGER,
            multiplier REAL,
            winnings REAL,
            profit REAL,
            ending_balance REAL,
            bomb_positions TEXT,
            notes TEXT,
            play_duration INTEGER
        )
        ''')
        
        # Session summary table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS session_summary (
            session_id TEXT PRIMARY KEY,
            start_time DATETIME,
            end_time DATETIME,
            initial_balance REAL,
            final_balance REAL,
            total_rounds INTEGER,
            total_wins INTEGER,
            total_losses INTEGER,
            net_profit REAL,
            win_rate REAL,
            max_balance REAL,
            min_balance REAL,
            avg_profit REAL,
            best_round_profit REAL,
            worst_round_profit REAL
        )
        ''')
        
        # Pattern analysis table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS pattern_analysis (
            pattern_id INTEGER PRIMARY KEY AUTOINCREMENT,
            safe_pick_count INTEGER,
            occurrence_count INTEGER,
            win_count INTEGER,
            avg_profit REAL,
            total_profit REAL,
            last_updated DATETIME
        )
        ''')
        
        conn.commit()
        conn.close()
    
    def create_widgets(self):
        """Create all GUI widgets"""
        # Configure styles
        self.configure_styles()
        
        # Main container with notebook (tabs)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Create tabs
        self.create_dashboard_tab()
        self.create_logger_tab()
        self.create_analytics_tab()
        self.create_charts_tab()
        self.create_import_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W, padding=5)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def configure_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        
        # Configure colors
        style.configure('Title.TLabel', font=('Arial', 16, 'bold'))
        style.configure('Heading.TLabel', font=('Arial', 12, 'bold'))
        style.configure('Success.TLabel', foreground=self.colors['win'])
        style.configure('Danger.TLabel', foreground=self.colors['loss'])
        style.configure('Accent.TButton', font=('Arial', 10, 'bold'))
    
    def create_dashboard_tab(self):
        """Create dashboard tab with overview"""
        self.dashboard_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.dashboard_frame, text='Dashboard')
        
        # Header
        header_frame = ttk.Frame(self.dashboard_frame)
        header_frame.pack(fill='x', padx=10, pady=10)
        
        ttk.Label(header_frame, text="Bomb Game Analytics Dashboard", 
                 style='Title.TLabel').pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="Refresh", 
                  command=self.refresh_dashboard).pack(side=tk.RIGHT)
        
        # Stats cards
        stats_frame = ttk.Frame(self.dashboard_frame)
        stats_frame.pack(fill='x', padx=10, pady=10)
        
        # Create stat cards
        self.stat_cards = {}
        stats = [
            ('balance', 'Current Balance', f"{self.current_balance:.2f} Sigils"),
            ('session', 'Current Session', self.current_session),
            ('rounds', 'Total Rounds', '0'),
            ('win_rate', 'Win Rate', '0%'),
            ('profit', 'Net Profit', '0.00'),
            ('streak', 'Current Streak', 'None')
        ]
        
        for i, (key, title, value) in enumerate(stats):
            card = self.create_stat_card(stats_frame, title, value, i)
            self.stat_cards[key] = card
        
        # Recent activity
        recent_frame = ttk.LabelFrame(self.dashboard_frame, text="Recent Activity", padding=10)
        recent_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Recent rounds table
        columns = ('time', 'bet', 'result', 'picks', 'multiplier', 'profit', 'balance')
        self.recent_tree = ttk.Treeview(recent_frame, columns=columns, show='headings', height=10)
        
        headings = {
            'time': 'Time',
            'bet': 'Bet',
            'result': 'Result',
            'picks': 'Safe Picks',
            'multiplier': 'Multiplier',
            'profit': 'Profit',
            'balance': 'Balance'
        }
        
        for col in columns:
            self.recent_tree.heading(col, text=headings[col])
            self.recent_tree.column(col, width=100)
        
        self.recent_tree.pack(fill='both', expand=True, side=tk.LEFT)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(recent_frame, orient=tk.VERTICAL, command=self.recent_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.recent_tree.configure(yscrollcommand=scrollbar.set)
    
    def create_stat_card(self, parent, title, value, col):
        """Create a statistics card"""
        card = ttk.Frame(parent, relief=tk.RAISED, borderwidth=2)
        card.grid(row=0, column=col, padx=5, pady=5, sticky='nsew')
        
        # Title
        ttk.Label(card, text=title, font=('Arial', 10)).pack(pady=(10, 5))
        
        # Value
        value_label = ttk.Label(card, text=value, font=('Arial', 14, 'bold'))
        value_label.pack(pady=(0, 10))
        
        # Configure grid
        parent.columnconfigure(col, weight=1)
        
        return {'frame': card, 'value_label': value_label}
    
    def create_logger_tab(self):
        """Create tab for logging game results"""
        self.logger_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.logger_frame, text='Log Results')
        
        # Create two columns
        left_frame = ttk.Frame(self.logger_frame)
        left_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=10, pady=10)
        
        right_frame = ttk.Frame(self.logger_frame)
        right_frame.pack(side=tk.RIGHT, fill='both', expand=True, padx=10, pady=10)
        
        # Session info
        session_frame = ttk.LabelFrame(left_frame, text="Session Info", padding=10)
        session_frame.pack(fill='x', pady=(0, 10))
        
        ttk.Label(session_frame, text="Session ID:").grid(row=0, column=0, sticky='w', pady=5)
        self.session_label = ttk.Label(session_frame, text=self.current_session, 
                                      font=('Arial', 10, 'bold'))
        self.session_label.grid(row=0, column=1, sticky='w', pady=5, padx=10)
        
        ttk.Label(session_frame, text="Balance:").grid(row=0, column=2, sticky='w', pady=5)
        self.balance_label = ttk.Label(session_frame, text=f"{self.current_balance:.2f} Sigils",
                                      font=('Arial', 10, 'bold'), foreground='green')
        self.balance_label.grid(row=0, column=3, sticky='w', pady=5, padx=10)
        
        # Game result form
        form_frame = ttk.LabelFrame(left_frame, text="Log Game Result", padding=15)
        form_frame.pack(fill='both', expand=True)
        
        # Form fields in grid
        row = 0
        
        # Bet amount
        ttk.Label(form_frame, text="Bet Amount (Sigils):").grid(row=row, column=0, sticky='w', pady=10)
        self.bet_var = tk.DoubleVar(value=0.1)
        ttk.Entry(form_frame, textvariable=self.bet_var, width=20).grid(row=row, column=1, pady=10, padx=10)
        row += 1
        
        # Strategy
        ttk.Label(form_frame, text="Strategy:").grid(row=row, column=0, sticky='w', pady=10)
        self.strategy_var = tk.StringVar(value='moderate')
        strategies = ['conservative', 'moderate', 'aggressive', 'max_risk']
        ttk.Combobox(form_frame, textvariable=self.strategy_var, 
                     values=strategies, state='readonly', width=20).grid(row=row, column=1, pady=10, padx=10)
        row += 1
        
        # Result
        ttk.Label(form_frame, text="Result:").grid(row=row, column=0, sticky='w', pady=10)
        self.result_var = tk.StringVar(value='win')
        ttk.Combobox(form_frame, textvariable=self.result_var, 
                     values=['win', 'loss'], state='readonly', width=20).grid(row=row, column=1, pady=10, padx=10)
        row += 1
        
        # Safe picks
        ttk.Label(form_frame, text="Safe Picks:").grid(row=row, column=0, sticky='w', pady=10)
        self.safe_picks_var = tk.IntVar(value=1)
        safe_picks_frame = ttk.Frame(form_frame)
        safe_picks_frame.grid(row=row, column=1, pady=10, padx=10, sticky='w')
        
        ttk.Spinbox(safe_picks_frame, from_=0, to=20, textvariable=self.safe_picks_var, 
                   width=5).pack(side=tk.LEFT)
        ttk.Label(safe_picks_frame, text=" (0-20)").pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Multiplier
        ttk.Label(form_frame, text="Multiplier:").grid(row=row, column=0, sticky='w', pady=10)
        self.multiplier_var = tk.DoubleVar(value=1.0)
        multiplier_frame = ttk.Frame(form_frame)
        multiplier_frame.grid(row=row, column=1, pady=10, padx=10, sticky='w')
        
        ttk.Entry(multiplier_frame, textvariable=self.multiplier_var, width=10).pack(side=tk.LEFT)
        ttk.Button(multiplier_frame, text="Auto", 
                  command=self.auto_calculate_multiplier).pack(side=tk.LEFT, padx=5)
        row += 1
        
        # Bomb positions (optional)
        ttk.Label(form_frame, text="Bomb Positions:").grid(row=row, column=0, sticky='w', pady=10)
        self.bomb_positions_var = tk.StringVar()
        ttk.Entry(form_frame, textvariable=self.bomb_positions_var, width=20).grid(row=row, column=1, pady=10, padx=10)
        row += 1
        
        # Notes
        ttk.Label(form_frame, text="Notes:").grid(row=row, column=0, sticky='nw', pady=10)
        self.notes_text = scrolledtext.ScrolledText(form_frame, width=30, height=8)
        self.notes_text.grid(row=row, column=1, pady=10, padx=10, sticky='w')
        row += 1
        
        # Buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        ttk.Button(button_frame, text="Log Result", command=self.log_result,
                  style='Accent.TButton').pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Calculate", 
                  command=self.calculate_result).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clear", 
                  command=self.clear_form).pack(side=tk.LEFT, padx=5)
        
        # Right side - Results display
        results_frame = ttk.LabelFrame(right_frame, text="Calculation Results", padding=15)
        results_frame.pack(fill='both', expand=True)
        
        # Results labels
        self.results_vars = {}
        result_fields = [
            ('Winnings:', 'winnings', '0.00 Sigils'),
            ('Profit/Loss:', 'profit', '0.00 Sigils'),
            ('New Balance:', 'new_balance', f"{self.current_balance:.2f} Sigils"),
            ('ROI:', 'roi', '0%'),
            ('Risk/Reward:', 'risk_reward', '0.00')
        ]
        
        for i, (label, key, default) in enumerate(result_fields):
            ttk.Label(results_frame, text=label, font=('Arial', 10)).grid(row=i, column=0, sticky='w', pady=10)
            self.results_vars[key] = tk.StringVar(value=default)
            ttk.Label(results_frame, textvariable=self.results_vars[key], 
                     font=('Arial', 10, 'bold')).grid(row=i, column=1, sticky='w', pady=10, padx=10)
        
        # Quick log buttons
        quick_frame = ttk.LabelFrame(right_frame, text="Quick Log Presets", padding=10)
        quick_frame.pack(fill='x', pady=10)
        
        presets = [
            ("Small Win (3 picks)", 0.1, 'win', 3, 1.9),
            ("Medium Win (5 picks)", 0.2, 'win', 5, 4.31),
            ("Big Win (8 picks)", 0.5, 'win', 8, 7.89),
            ("Loss (2 picks)", 0.1, 'loss', 2, 0)
        ]
        
        for i, (text, bet, result, picks, mult) in enumerate(presets):
            btn = ttk.Button(quick_frame, text=text,
                           command=lambda b=bet, r=result, p=picks, m=mult: 
                           self.apply_preset(b, r, p, m))
            btn.grid(row=i//2, column=i%2, padx=5, pady=5, sticky='ew')
        
        # Session stats
        stats_frame = ttk.LabelFrame(right_frame, text="Session Statistics", padding=10)
        stats_frame.pack(fill='both', expand=True, pady=10)
        
        self.session_stats_text = scrolledtext.ScrolledText(stats_frame, height=10)
        self.session_stats_text.pack(fill='both', expand=True)
    
    def create_analytics_tab(self):
        """Create analytics tab with detailed statistics"""
        self.analytics_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.analytics_frame, text='Analytics')
        
        # Create notebook for analytics subtabs
        analytics_notebook = ttk.Notebook(self.analytics_frame)
        analytics_notebook.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Summary tab
        summary_tab = ttk.Frame(analytics_notebook)
        analytics_notebook.add(summary_tab, text='Summary')
        
        self.summary_text = scrolledtext.ScrolledText(summary_tab, wrap=tk.WORD)
        self.summary_text.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Performance tab
        perf_tab = ttk.Frame(analytics_notebook)
        analytics_notebook.add(perf_tab, text='Performance')
        
        # Performance metrics
        perf_frame = ttk.Frame(perf_tab)
        perf_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Performance treeview
        perf_columns = ('metric', 'value', 'description')
        self.perf_tree = ttk.Treeview(perf_frame, columns=perf_columns, show='headings', height=15)
        
        for col in perf_columns:
            self.perf_tree.heading(col, text=col.title())
            self.perf_tree.column(col, width=200)
        
        self.perf_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # Pattern analysis tab
        pattern_tab = ttk.Frame(analytics_notebook)
        analytics_notebook.add(pattern_tab, text='Patterns')
        
        # Pattern treeview
        pattern_frame = ttk.Frame(pattern_tab)
        pattern_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        pattern_columns = ('safe_picks', 'games', 'wins', 'win_rate', 'avg_profit', 'total_profit')
        self.pattern_tree = ttk.Treeview(pattern_frame, columns=pattern_columns, show='headings', height=15)
        
        headings = {
            'safe_picks': 'Safe Picks',
            'games': 'Games',
            'wins': 'Wins',
            'win_rate': 'Win Rate',
            'avg_profit': 'Avg Profit',
            'total_profit': 'Total Profit'
        }
        
        for col in pattern_columns:
            self.pattern_tree.heading(col, text=headings.get(col, col.title()))
            self.pattern_tree.column(col, width=100)
        
        self.pattern_tree.pack(side=tk.LEFT, fill='both', expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(pattern_frame, orient=tk.VERTICAL, command=self.pattern_tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.pattern_tree.configure(yscrollcommand=scrollbar.set)
        
        # Strategy analysis tab
        strategy_tab = ttk.Frame(analytics_notebook)
        analytics_notebook.add(strategy_tab, text='Strategies')
        
        self.strategy_text = scrolledtext.ScrolledText(strategy_tab, wrap=tk.WORD)
        self.strategy_text.pack(fill='both', expand=True, padx=10, pady=10)
    
    def create_charts_tab(self):
        """Create charts tab with visualizations"""
        self.charts_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.charts_frame, text='Charts')
        
        # Control panel
        control_frame = ttk.Frame(self.charts_frame)
        control_frame.pack(fill='x', padx=10, pady=10)
        
        # Chart type selection
        ttk.Label(control_frame, text="Chart Type:").pack(side=tk.LEFT, padx=5)
        self.chart_type_var = tk.StringVar(value='balance')
        chart_types = [
            ('Balance History', 'balance'),
            ('Profit Distribution', 'profit_dist'),
            ('Win/Loss Ratio', 'win_loss'),
            ('Safe Picks Heatmap', 'heatmap'),
            ('Multiplier Analysis', 'multiplier'),
            ('Daily Performance', 'daily'),
            ('Risk Analysis', 'risk')
        ]
        
        for text, value in chart_types:
            ttk.Radiobutton(control_frame, text=text, variable=self.chart_type_var,
                           value=value).pack(side=tk.LEFT, padx=5)
        
        # Generate button
        ttk.Button(control_frame, text="Generate Chart", 
                  command=self.generate_chart).pack(side=tk.LEFT, padx=20)
        
        # Chart display area
        self.chart_display_frame = ttk.Frame(self.charts_frame)
        self.chart_display_frame.pack(fill='both', expand=True, padx=10, pady=10)
    
    def create_import_tab(self):
        """Create import/export tab"""
        self.import_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.import_frame, text='Import/Export')
        
        # Import section
        import_frame = ttk.LabelFrame(self.import_frame, text="Import Data", padding=15)
        import_frame.pack(fill='x', padx=10, pady=10)
        
        # CSV import
        csv_frame = ttk.Frame(import_frame)
        csv_frame.pack(fill='x', pady=5)
        
        ttk.Label(csv_frame, text="CSV File:").pack(side=tk.LEFT)
        self.csv_path_var = tk.StringVar()
        ttk.Entry(csv_frame, textvariable=self.csv_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(csv_frame, text="Browse", 
                  command=self.browse_csv).pack(side=tk.LEFT, padx=5)
        ttk.Button(csv_frame, text="Import", 
                  command=self.import_csv).pack(side=tk.LEFT, padx=5)
        
        # JSON import
        json_frame = ttk.Frame(import_frame)
        json_frame.pack(fill='x', pady=5)
        
        ttk.Label(json_frame, text="JSON File:").pack(side=tk.LEFT)
        self.json_path_var = tk.StringVar()
        ttk.Entry(json_frame, textvariable=self.json_path_var, width=40).pack(side=tk.LEFT, padx=5)
        ttk.Button(json_frame, text="Browse", 
                  command=self.browse_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(json_frame, text="Import", 
                  command=self.import_json).pack(side=tk.LEFT, padx=5)
        
        # Export section
        export_frame = ttk.LabelFrame(self.import_frame, text="Export Data", padding=15)
        export_frame.pack(fill='x', padx=10, pady=10)
        
        # Export buttons
        ttk.Button(export_frame, text="Export Session to CSV", 
                  command=self.export_session_csv).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(export_frame, text="Export All to CSV", 
                  command=self.export_all_csv).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(export_frame, text="Export Statistics Report", 
                  command=self.export_report).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(export_frame, text="Backup Database", 
                  command=self.backup_database).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Database info
        info_frame = ttk.LabelFrame(self.import_frame, text="Database Information", padding=15)
        info_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        self.db_info_text = scrolledtext.ScrolledText(info_frame, height=10)
        self.db_info_text.pack(fill='both', expand=True)
    
    def load_initial_data(self):
        """Load initial data into GUI"""
        self.refresh_dashboard()
        self.update_session_stats()
    
    def refresh_dashboard(self):
        """Refresh dashboard with latest data"""
        # Update stat cards
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get session stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_rounds,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as net_profit
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        stats = cursor.fetchone()
        total_rounds, wins, net_profit = stats if stats[0] else (0, 0, 0)
        
        win_rate = (wins / total_rounds * 100) if total_rounds > 0 else 0
        
        # Update stat cards
        self.stat_cards['balance']['value_label'].config(text=f"{self.current_balance:.2f} Sigils")
        self.stat_cards['session']['value_label'].config(text=self.current_session[:15])
        self.stat_cards['rounds']['value_label'].config(text=str(total_rounds))
        self.stat_cards['win_rate']['value_label'].config(text=f"{win_rate:.1f}%")
        self.stat_cards['profit']['value_label'].config(text=f"{net_profit:+.2f}")
        
        # Get current streak
        cursor.execute('''
            SELECT result FROM game_results 
            WHERE session_id = ? 
            ORDER BY timestamp DESC LIMIT 5
        ''', (self.current_session,))
        
        results = [row[0] for row in cursor.fetchall()]
        streak = 0
        if results:
            last_result = results[0]
            for r in results:
                if r == last_result:
                    streak += 1
                else:
                    break
        
        self.stat_cards['streak']['value_label'].config(
            text=f"{streak} {last_result if results else ''}"
        )
        
        # Load recent activity
        for item in self.recent_tree.get_children():
            self.recent_tree.delete(item)
        
        cursor.execute('''
            SELECT 
                strftime('%H:%M', timestamp) as time,
                bet_amount,
                result,
                safe_picks,
                multiplier,
                profit,
                ending_balance
            FROM game_results 
            WHERE session_id = ?
            ORDER BY timestamp DESC 
            LIMIT 10
        ''', (self.current_session,))
        
        for row in cursor.fetchall():
            time_str, bet, result, picks, mult, profit, balance = row
            self.recent_tree.insert('', 'end', values=(
                time_str,
                f"{bet:.2f}",
                result.upper(),
                picks,
                f"{mult:.2f}x",
                f"{profit:+.2f}",
                f"{balance:.2f}"
            ), tags=(result,))
        
        # Configure tags for coloring
        self.recent_tree.tag_configure('win', background='#e8f5e9')
        self.recent_tree.tag_configure('loss', background='#ffebee')
        
        conn.close()
    
    def log_result(self):
        """Log a game result to database"""
        try:
            # Get values from form
            bet = self.bet_var.get()
            strategy = self.strategy_var.get()
            result = self.result_var.get()
            safe_picks = self.safe_picks_var.get()
            multiplier = self.multiplier_var.get()
            bomb_positions = self.bomb_positions_var.get()
            notes = self.notes_text.get("1.0", tk.END).strip()
            
            # Calculate winnings and profit
            if result == 'win':
                winnings = bet * multiplier
                profit = winnings - bet
            else:
                winnings = 0
                profit = -bet
            
            # Update balance
            new_balance = self.current_balance + profit
            
            # Get next round number
            round_num = self.get_next_round_number()
            
            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO game_results 
                (session_id, round_number, bet_amount, strategy, result, 
                 safe_picks, multiplier, winnings, profit, ending_balance,
                 bomb_positions, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (self.current_session, round_num, bet, strategy, result,
                  safe_picks, multiplier, winnings, profit, new_balance,
                  bomb_positions, notes))
            
            conn.commit()
            
            # Update pattern analysis
            self.update_pattern_analysis(conn, safe_picks, result, profit)
            
            conn.close()
            
            # Update current balance
            self.current_balance = new_balance
            
            # Update UI
            self.balance_label.config(text=f"{self.current_balance:.2f} Sigils")
            self.refresh_dashboard()
            self.update_session_stats()
            self.update_analytics()
            
            # Show success message
            self.status_var.set(f"Result logged! Round #{round_num}, Profit: {profit:+.2f}")
            
            # Clear form for next entry
            self.clear_form()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to log result: {str(e)}")
            self.status_var.set(f"Error: {str(e)}")
    
    def calculate_result(self):
        """Calculate and display results without logging"""
        try:
            bet = self.bet_var.get()
            result = self.result_var.get()
            multiplier = self.multiplier_var.get()
            
            if result == 'win':
                winnings = bet * multiplier
                profit = winnings - bet
                roi = (profit / bet) * 100
                risk_reward = profit / bet if bet > 0 else 0
            else:
                winnings = 0
                profit = -bet
                roi = -100
                risk_reward = -1
            
            new_balance = self.current_balance + profit
            
            # Update results display
            self.results_vars['winnings'].set(f"{winnings:.2f} Sigils")
            self.results_vars['profit'].set(f"{profit:+.2f} Sigils")
            self.results_vars['new_balance'].set(f"{new_balance:.2f} Sigils")
            self.results_vars['roi'].set(f"{roi:+.1f}%")
            self.results_vars['risk_reward'].set(f"{risk_reward:+.2f}")
            
        except Exception as e:
            messagebox.showerror("Error", f"Calculation error: {str(e)}")
    
    def auto_calculate_multiplier(self):
        """Automatically calculate multiplier based on safe picks"""
        safe_picks = self.safe_picks_var.get()
        if 0 <= safe_picks < len(self.MULTIPLIERS):
            multiplier = self.MULTIPLIERS[safe_picks]
            self.multiplier_var.set(multiplier)
            self.calculate_result()
    
    def apply_preset(self, bet, result, picks, multiplier):
        """Apply preset values to form"""
        self.bet_var.set(bet)
        self.result_var.set(result)
        self.safe_picks_var.set(picks)
        self.multiplier_var.set(multiplier)
        self.calculate_result()
    
    def clear_form(self):
        """Clear the form"""
        self.bet_var.set(0.1)
        self.strategy_var.set('moderate')
        self.result_var.set('win')
        self.safe_picks_var.set(1)
        self.multiplier_var.set(1.0)
        self.bomb_positions_var.set('')
        self.notes_text.delete("1.0", tk.END)
        self.calculate_result()
    
    def get_next_round_number(self):
        """Get next round number for current session"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT MAX(round_number) 
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        result = cursor.fetchone()
        next_round = (result[0] + 1) if result[0] else 1
        
        conn.close()
        return next_round
    
    def update_session_stats(self):
        """Update session statistics display"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get detailed session stats
        cursor.execute('''
            SELECT 
                COUNT(*) as total_rounds,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) as losses,
                SUM(profit) as net_profit,
                AVG(profit) as avg_profit,
                MIN(profit) as worst_loss,
                MAX(profit) as best_win,
                MIN(ending_balance) as min_balance,
                MAX(ending_balance) as max_balance,
                AVG(safe_picks) as avg_safe_picks
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        stats = cursor.fetchone()
        
        self.session_stats_text.delete("1.0", tk.END)
        
        if stats and stats[0]:
            total, wins, losses, net_profit, avg_profit, worst, best, min_bal, max_bal, avg_picks = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            
            stats_text = f"""SESSION STATISTICS
{'='*40}
Total Rounds: {total}
Wins: {wins} ({win_rate:.1f}%)
Losses: {losses}
Net Profit: {net_profit:+.2f} Sigils
Average Profit/Round: {avg_profit:.2f} Sigils
Best Win: {best:+.2f} Sigils
Worst Loss: {worst:+.2f} Sigils
Current Balance: {self.current_balance:.2f} Sigils
Minimum Balance: {min_bal:.2f} Sigils
Maximum Balance: {max_bal:.2f} Sigils
Average Safe Picks: {avg_picks:.1f}

PERFORMANCE METRICS
{'='*40}
Expected Value: {avg_profit:.4f}
Risk of Ruin: {(losses/total*100):.1f}%
Profit Factor: {(-net_profit/(worst*total) if worst < 0 else 'N/A')}
Sharpe Ratio: {(avg_profit/(abs(avg_profit - worst) + 0.001)):.2f}
"""
            self.session_stats_text.insert("1.0", stats_text)
        
        conn.close()
    
    def update_pattern_analysis(self, conn, safe_picks, result, profit):
        """Update pattern analysis in database"""
        cursor = conn.cursor()
        
        # Check if pattern exists
        cursor.execute('''
            SELECT * FROM pattern_analysis 
            WHERE safe_pick_count = ?
        ''', (safe_picks,))
        
        existing = cursor.fetchone()
        
        if existing:
            # Update existing pattern
            pattern_id, _, old_count, old_wins, old_avg, old_total, _ = existing
            new_count = old_count + 1
            new_wins = old_wins + (1 if result == 'win' else 0)
            new_total = old_total + profit
            new_avg = new_total / new_count
            
            cursor.execute('''
                UPDATE pattern_analysis 
                SET occurrence_count = ?, win_count = ?, avg_profit = ?, 
                    total_profit = ?, last_updated = CURRENT_TIMESTAMP
                WHERE pattern_id = ?
            ''', (new_count, new_wins, new_avg, new_total, pattern_id))
        else:
            # Insert new pattern
            win_count = 1 if result == 'win' else 0
            cursor.execute('''
                INSERT INTO pattern_analysis 
                (safe_pick_count, occurrence_count, win_count, avg_profit, total_profit)
                VALUES (?, 1, ?, ?, ?)
            ''', (safe_picks, win_count, profit, profit))
        
        conn.commit()
    
    def update_analytics(self):
        """Update analytics tabs with latest data"""
        self.update_summary_analysis()
        self.update_performance_metrics()
        self.update_pattern_display()
        self.update_strategy_analysis()
    
    def update_summary_analysis(self):
        """Update summary analysis tab"""
        conn = sqlite3.connect(self.db_path)
        
        # Get comprehensive summary
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as total_profit,
                AVG(profit) as avg_profit,
                STDDEV(profit) as std_profit,
                MIN(profit) as min_profit,
                MAX(profit) as max_profit,
                AVG(safe_picks) as avg_safe_picks,
                SUM(bet_amount) as total_bet
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        stats = cursor.fetchone()
        
        self.summary_text.delete("1.0", tk.END)
        
        if stats and stats[0]:
            total, wins, total_profit, avg_profit, std_profit, min_profit, max_profit, avg_picks, total_bet = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            
            summary = f"""COMPREHENSIVE ANALYSIS REPORT
{'='*60}
Session: {self.current_session}
Report Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

OVERALL PERFORMANCE
{'='*60}
Total Games Played: {total}
Total Wins: {wins} ({win_rate:.1f}%)
Total Losses: {total - wins}
Net Profit: {total_profit:+.2f} Sigils
Total Amount Bet: {total_bet:.2f} Sigils
Return on Investment: {(total_profit/total_bet*100 if total_bet > 0 else 0):+.1f}%

PROFIT ANALYSIS
{'='*60}
Average Profit/Game: {avg_profit:.4f} Sigils
Profit Standard Deviation: {std_profit if std_profit else 0:.4f} Sigils
Best Single Game Profit: {max_profit:+.2f} Sigils
Worst Single Game Loss: {min_profit:+.2f} Sigils
Profit Range: {max_profit - min_profit:.2f} Sigils

GAME CHARACTERISTICS
{'='*60}
Average Safe Picks: {avg_picks:.2f}
Expected Value per Game: {avg_profit:.4f} Sigils
Risk per Game (Std Dev): {std_profit if std_profit else 0:.4f} Sigils
Sharpe Ratio: {(avg_profit/(std_profit + 0.001) if std_profit else 0):.2f}

PERFORMANCE BANDS
{'='*60}
Excellent: Profit > {avg_profit + (std_profit if std_profit else 0):.2f}
Average: {avg_profit - (std_profit if std_profit else 0):.2f} < Profit < {avg_profit + (std_profit if std_profit else 0):.2f}
Poor: Profit < {avg_profit - (std_profit if std_profit else 0):.2f}

RECOMMENDATIONS
{'='*60}
"""
            
            # Add recommendations based on stats
            if win_rate > 60:
                summary += "✓ Excellent win rate! Consider increasing bet sizes gradually.\n"
            elif win_rate > 45:
                summary += "✓ Good performance. Maintain current strategy.\n"
            else:
                summary += "⚠ Consider adjusting strategy or reducing bet sizes.\n"
            
            if avg_profit > 0:
                summary += "✓ Positive expected value. Strategy is profitable.\n"
            else:
                summary += "⚠ Negative expected value. Review and adjust strategy.\n"
            
            if std_profit and std_profit > abs(avg_profit) * 3:
                summary += "⚠ High volatility. Consider more conservative plays.\n"
            
            self.summary_text.insert("1.0", summary)
        
        conn.close()
    
    def update_performance_metrics(self):
        """Update performance metrics treeview"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing items
        for item in self.perf_tree.get_children():
            self.perf_tree.delete(item)
        
        # Calculate various performance metrics
        cursor.execute('''
            SELECT 
                profit,
                result,
                bet_amount,
                safe_picks
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        games = cursor.fetchall()
        
        if games:
            profits = [g[0] for g in games]
            results = [g[1] for g in games]
            bets = [g[2] for g in games]
            picks = [g[3] for g in games]
            
            # Calculate metrics
            metrics = [
                ("Total Games", len(games), "Number of games played"),
                ("Win Rate", f"{(results.count('win')/len(games)*100):.1f}%", "Percentage of wins"),
                ("Net Profit", f"{sum(profits):+.2f}", "Total profit/loss"),
                ("Avg Profit", f"{np.mean(profits):.4f}", "Average profit per game"),
                ("Std Dev", f"{np.std(profits):.4f}", "Profit volatility"),
                ("Max Profit", f"{max(profits):+.2f}", "Best single game profit"),
                ("Min Profit", f"{min(profits):+.2f}", "Worst single game loss"),
                ("Avg Bet", f"{np.mean(bets):.2f}", "Average bet size"),
                ("Avg Safe Picks", f"{np.mean(picks):.2f}", "Average safe picks"),
                ("Profit Factor", f"{(sum(p for p in profits if p > 0)/abs(sum(p for p in profits if p < 0)) if any(p < 0 for p in profits) else '∞'):.2f}", "Profit/Loss ratio"),
                ("Expectancy", f"{(np.mean(profits)/np.mean(bets) if np.mean(bets) > 0 else 0):.3f}", "Avg profit per unit bet"),
                ("Risk of Ruin", f"{(results.count('loss')/len(games)*100):.1f}%", "Probability of losing"),
                ("Sharpe Ratio", f"{(np.mean(profits)/(np.std(profits)+0.001)):.3f}", "Risk-adjusted return"),
                ("Max Drawdown", f"{min(profits):+.2f}", "Maximum single loss"),
                ("Recovery Factor", f"{(-sum(profits)/min(profits) if min(profits) < 0 else '∞'):.2f}", "Profit/Max loss ratio")
            ]
            
            for metric, value, desc in metrics:
                self.perf_tree.insert('', 'end', values=(metric, value, desc))
        
        conn.close()
    
    def update_pattern_display(self):
        """Update pattern analysis display"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Clear existing items
        for item in self.pattern_tree.get_children():
            self.pattern_tree.delete(item)
        
        # Get pattern analysis
        cursor.execute('''
            SELECT 
                safe_pick_count,
                occurrence_count,
                win_count,
                (win_count * 100.0 / occurrence_count) as win_rate,
                avg_profit,
                total_profit
            FROM pattern_analysis 
            WHERE occurrence_count > 0
            ORDER BY avg_profit DESC
        ''')
        
        patterns = cursor.fetchall()
        
        for pattern in patterns:
            safe_picks, games, wins, win_rate, avg_profit, total_profit = pattern
            self.pattern_tree.insert('', 'end', values=(
                safe_picks,
                games,
                wins,
                f"{win_rate:.1f}%" if win_rate else "0.0%",
                f"{avg_profit:.4f}",
                f"{total_profit:.2f}"
            ))
        
        conn.close()
    
    def update_strategy_analysis(self):
        """Update strategy analysis"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Analyze strategies
        cursor.execute('''
            SELECT 
                strategy,
                COUNT(*) as games,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                AVG(profit) as avg_profit,
                SUM(profit) as total_profit,
                AVG(safe_picks) as avg_picks
            FROM game_results 
            WHERE session_id = ?
            GROUP BY strategy
            ORDER BY avg_profit DESC
        ''', (self.current_session,))
        
        strategies = cursor.fetchall()
        
        self.strategy_text.delete("1.0", tk.END)
        
        if strategies:
            analysis = "STRATEGY PERFORMANCE ANALYSIS\n"
            analysis += "=" * 50 + "\n\n"
            
            for strategy, games, wins, avg_profit, total_profit, avg_picks in strategies:
                win_rate = (wins / games * 100) if games > 0 else 0
                
                analysis += f"Strategy: {strategy.upper()}\n"
                analysis += f"{'-'*30}\n"
                analysis += f"Games Played: {games}\n"
                analysis += f"Win Rate: {win_rate:.1f}%\n"
                analysis += f"Average Profit: {avg_profit:.4f}\n"
                analysis += f"Total Profit: {total_profit:.2f}\n"
                analysis += f"Average Safe Picks: {avg_picks:.1f}\n"
                
                # Add recommendation
                if avg_profit > 0:
                    analysis += f"✓ RECOMMENDED (Positive EV: {avg_profit:.4f})\n"
                else:
                    analysis += f"⚠ NOT RECOMMENDED (Negative EV: {avg_profit:.4f})\n"
                
                analysis += "\n"
            
            # Find best strategy
            if strategies:
                best_strat = max(strategies, key=lambda x: x[3])  # Index 3 is avg_profit
                analysis += f"\nBEST PERFORMING STRATEGY: {best_strat[0].upper()}\n"
                analysis += f"Average Profit: {best_strat[3]:.4f}\n"
                analysis += f"Win Rate: {(best_strat[2]/best_strat[1]*100):.1f}%\n"
            
            self.strategy_text.insert("1.0", analysis)
        
        conn.close()
    
    def generate_chart(self):
        """Generate selected chart"""
        chart_type = self.chart_type_var.get()
        
        # Clear previous chart
        for widget in self.chart_display_frame.winfo_children():
            widget.destroy()
        
        conn = sqlite3.connect(self.db_path)
        
        try:
            if chart_type == 'balance':
                self.generate_balance_chart(conn)
            elif chart_type == 'profit_dist':
                self.generate_profit_distribution_chart(conn)
            elif chart_type == 'win_loss':
                self.generate_win_loss_chart(conn)
            elif chart_type == 'heatmap':
                self.generate_heatmap_chart(conn)
            elif chart_type == 'multiplier':
                self.generate_multiplier_chart(conn)
            elif chart_type == 'daily':
                self.generate_daily_chart(conn)
            elif chart_type == 'risk':
                self.generate_risk_chart(conn)
                
        except Exception as e:
            messagebox.showerror("Chart Error", f"Failed to generate chart: {str(e)}")
        finally:
            conn.close()
    
    def generate_balance_chart(self, conn):
        """Generate balance over time chart"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT timestamp, ending_balance 
            FROM game_results 
            WHERE session_id = ?
            ORDER BY timestamp
        ''', (self.current_session,))
        
        data = cursor.fetchall()
        
        if data:
            # Create figure
            fig, ax = plt.subplots(figsize=(12, 6))
            
            # Prepare data
            timestamps = [datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S') for row in data]
            balances = [row[1] for row in data]
            
            # Plot
            ax.plot(timestamps, balances, 'b-', linewidth=2, marker='o', markersize=4)
            ax.axhline(y=self.current_balance, color='g', linestyle='--', alpha=0.7, 
                      label=f'Current: {self.current_balance:.2f}')
            
            # Formatting
            ax.set_xlabel('Time', fontsize=12)
            ax.set_ylabel('Balance (Sigils)', fontsize=12)
            ax.set_title('Balance Evolution Over Time', fontsize=14, fontweight='bold')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            # Display in GUI
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_profit_distribution_chart(self, conn):
        """Generate profit distribution histogram"""
        cursor = conn.cursor()
        cursor.execute('SELECT profit FROM game_results WHERE session_id = ?', 
                      (self.current_session,))
        
        profits = [row[0] for row in cursor.fetchall()]
        
        if profits:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Histogram
            ax1.hist(profits, bins=20, edgecolor='black', alpha=0.7, color='skyblue')
            ax1.axvline(x=np.mean(profits), color='red', linestyle='--', 
                       label=f'Mean: {np.mean(profits):.2f}')
            ax1.set_xlabel('Profit/Loss (Sigils)')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Profit Distribution Histogram')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
            
            # Box plot
            ax2.boxplot(profits, vert=False)
            ax2.set_xlabel('Profit/Loss (Sigils)')
            ax2.set_title('Profit Distribution Box Plot')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_win_loss_chart(self, conn):
        """Generate win/loss ratio chart"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT result, COUNT(*) 
            FROM game_results 
            WHERE session_id = ?
            GROUP BY result
        ''', (self.current_session,))
        
        data = dict(cursor.fetchall())
        
        if data:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 6))
            
            # Pie chart
            labels = list(data.keys())
            sizes = list(data.values())
            colors = ['#2ecc71', '#e74c3c']
            
            ax1.pie(sizes, labels=labels, autopct='%1.1f%%', colors=colors, 
                   startangle=90, shadow=True)
            ax1.axis('equal')
            ax1.set_title('Win/Loss Ratio')
            
            # Bar chart
            ax2.bar(labels, sizes, color=colors, alpha=0.7)
            ax2.set_xlabel('Result')
            ax2.set_ylabel('Count')
            ax2.set_title('Win/Loss Count')
            ax2.grid(True, alpha=0.3)
            
            # Add value labels on bars
            for i, v in enumerate(sizes):
                ax2.text(i, v + 0.5, str(v), ha='center')
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_heatmap_chart(self, conn):
        """Generate safe picks heatmap"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT safe_picks, result, COUNT(*)
            FROM game_results 
            WHERE session_id = ?
            GROUP BY safe_picks, result
        ''', (self.current_session,))
        
        data = cursor.fetchall()
        
        if data:
            # Create pivot table
            df = pd.DataFrame(data, columns=['safe_picks', 'result', 'count'])
            pivot = df.pivot(index='safe_picks', columns='result', values='count').fillna(0)
            
            fig, ax = plt.subplots(figsize=(10, 6))
            
            # Create heatmap
            sns.heatmap(pivot, annot=True, fmt='g', cmap='YlOrRd', ax=ax)
            ax.set_xlabel('Result')
            ax.set_ylabel('Safe Picks')
            ax.set_title('Safe Picks vs Result Heatmap')
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_multiplier_chart(self, conn):
        """Generate multiplier analysis chart"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT multiplier, COUNT(*), AVG(profit)
            FROM game_results 
            WHERE session_id = ? AND result = 'win'
            GROUP BY multiplier
            ORDER BY multiplier
        ''', (self.current_session,))
        
        data = cursor.fetchall()
        
        if data:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            multipliers = [row[0] for row in data]
            counts = [row[1] for row in data]
            avg_profits = [row[2] for row in data]
            
            # Frequency chart
            ax1.bar(range(len(multipliers)), counts, alpha=0.7, color='blue')
            ax1.set_xlabel('Multiplier')
            ax1.set_ylabel('Frequency')
            ax1.set_title('Multiplier Frequency Distribution')
            ax1.set_xticks(range(len(multipliers)))
            ax1.set_xticklabels([f'{m:.2f}x' for m in multipliers], rotation=45)
            ax1.grid(True, alpha=0.3)
            
            # Profit vs Multiplier
            ax2.scatter(multipliers, avg_profits, s=100, alpha=0.7, color='red')
            ax2.set_xlabel('Multiplier')
            ax2.set_ylabel('Average Profit')
            ax2.set_title('Profit vs Multiplier')
            ax2.grid(True, alpha=0.3)
            
            # Add trend line
            if len(multipliers) > 1:
                z = np.polyfit(multipliers, avg_profits, 1)
                p = np.poly1d(z)
                ax2.plot(multipliers, p(multipliers), "r--", alpha=0.5)
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_daily_chart(self, conn):
        """Generate daily performance chart"""
        cursor = conn.cursor()
        cursor.execute('''
            SELECT DATE(timestamp) as date, 
                   SUM(profit) as daily_profit,
                   COUNT(*) as daily_games
            FROM game_results 
            WHERE session_id = ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        ''', (self.current_session,))
        
        data = cursor.fetchall()
        
        if data:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            dates = [row[0] for row in data]
            profits = [row[1] for row in data]
            games = [row[2] for row in data]
            
            # Daily profit
            bars = ax1.bar(dates, profits, alpha=0.7, color=['green' if p > 0 else 'red' for p in profits])
            ax1.set_xlabel('Date')
            ax1.set_ylabel('Daily Profit (Sigils)')
            ax1.set_title('Daily Profit Performance')
            ax1.grid(True, alpha=0.3)
            
            # Add value labels
            for bar, profit in zip(bars, profits):
                height = bar.get_height()
                ax1.text(bar.get_x() + bar.get_width()/2., height,
                        f'{profit:+.1f}', ha='center', va='bottom' if profit > 0 else 'top')
            
            # Daily games
            ax2.bar(dates, games, alpha=0.7, color='blue')
            ax2.set_xlabel('Date')
            ax2.set_ylabel('Number of Games')
            ax2.set_title('Daily Game Volume')
            ax2.grid(True, alpha=0.3)
            
            plt.xticks(rotation=45)
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def generate_risk_chart(self, conn):
        """Generate risk analysis chart"""
        cursor = conn.cursor()
        cursor.execute('SELECT profit FROM game_results WHERE session_id = ?', 
                      (self.current_session,))
        
        profits = [row[0] for row in cursor.fetchall()]
        
        if profits:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
            
            # Cumulative profit
            cumulative = np.cumsum(profits)
            ax1.plot(range(len(cumulative)), cumulative, 'b-', linewidth=2)
            ax1.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            ax1.fill_between(range(len(cumulative)), 0, cumulative, 
                            where=cumulative >= 0, color='green', alpha=0.3)
            ax1.fill_between(range(len(cumulative)), 0, cumulative, 
                            where=cumulative < 0, color='red', alpha=0.3)
            ax1.set_xlabel('Game Number')
            ax1.set_ylabel('Cumulative Profit (Sigils)')
            ax1.set_title('Cumulative Profit Curve')
            ax1.grid(True, alpha=0.3)
            
            # Drawdown analysis
            running_max = np.maximum.accumulate(cumulative)
            drawdown = (cumulative - running_max) / (running_max + 0.001)
            
            ax2.fill_between(range(len(drawdown)), drawdown, 0, 
                            where=drawdown < 0, color='red', alpha=0.3)
            ax2.set_xlabel('Game Number')
            ax2.set_ylabel('Drawdown (%)')
            ax2.set_title('Drawdown Analysis')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, self.chart_display_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
    
    def browse_csv(self):
        """Browse for CSV file"""
        filename = filedialog.askopenfilename(
            title="Select CSV File",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        if filename:
            self.csv_path_var.set(filename)
    
    def browse_json(self):
        """Browse for JSON file"""
        filename = filedialog.askopenfilename(
            title="Select JSON File",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if filename:
            self.json_path_var.set(filename)
    
    def import_csv(self):
        """Import data from CSV"""
        # Implementation would go here
        messagebox.showinfo("Import CSV", "CSV import functionality would be implemented here")
    
    def import_json(self):
        """Import data from JSON"""
        # Implementation would go here
        messagebox.showinfo("Import JSON", "JSON import functionality would be implemented here")
    
    def export_session_csv(self):
        """Export current session to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"{self.current_session}.csv"
        )
        
        if filename:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT * FROM game_results 
                WHERE session_id = ?
                ORDER BY timestamp
            ''', (self.current_session,))
            
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(rows)
            
            conn.close()
            
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(rows)} rows to {filename}")
            self.status_var.set(f"Exported session to {filename}")
    
    def export_all_csv(self):
        """Export all data to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="all_game_results.csv"
        )
        
        if filename:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('SELECT * FROM game_results ORDER BY timestamp')
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(columns)
                writer.writerows(rows)
            
            conn.close()
            
            messagebox.showinfo("Export Complete", 
                              f"Exported {len(rows)} rows to {filename}")
            self.status_var.set(f"Exported all data to {filename}")
    
    def export_report(self):
        """Export comprehensive report"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
            initialfile=f"game_report_{self.current_session}.txt"
        )
        
        if filename:
            # Gather data and generate report
            report_content = self.generate_report_content()
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(report_content)
            
            messagebox.showinfo("Report Generated", 
                              f"Report saved to {filename}")
            self.status_var.set(f"Report exported to {filename}")
    
    def generate_report_content(self):
        """Generate comprehensive report content"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get session data
        cursor.execute('''
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) as wins,
                SUM(profit) as total_profit,
                AVG(profit) as avg_profit,
                MIN(profit) as min_profit,
                MAX(profit) as max_profit,
                STDDEV(profit) as std_profit,
                AVG(safe_picks) as avg_safe_picks
            FROM game_results 
            WHERE session_id = ?
        ''', (self.current_session,))
        
        stats = cursor.fetchone()
        
        report = "=" * 70 + "\n"
        report += "BOMB GAME ANALYTICS REPORT\n"
        report += "=" * 70 + "\n\n"
        
        report += f"Session: {self.current_session}\n"
        report += f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        report += f"Current Balance: {self.current_balance:.2f} Sigils\n\n"
        
        if stats and stats[0]:
            total, wins, total_profit, avg_profit, min_profit, max_profit, std_profit, avg_picks = stats
            win_rate = (wins / total * 100) if total > 0 else 0
            
            report += "PERFORMANCE SUMMARY\n"
            report += "-" * 50 + "\n"
            report += f"Total Games: {total}\n"
            report += f"Wins: {wins} ({win_rate:.1f}%)\n"
            report += f"Losses: {total - wins}\n"
            report += f"Net Profit: {total_profit:+.2f} Sigils\n"
            report += f"Average Profit/Game: {avg_profit:.4f} Sigils\n"
            report += f"Best Win: {max_profit:+.2f} Sigils\n"
            report += f"Worst Loss: {min_profit:+.2f} Sigils\n"
            report += f"Volatility (Std Dev): {std_profit if std_profit else 0:.4f} Sigils\n"
            report += f"Average Safe Picks: {avg_picks:.2f}\n\n"
            
            # Risk metrics
            sharpe = avg_profit / (std_profit + 0.001) if std_profit else 0
            report += "RISK METRICS\n"
            report += "-" * 50 + "\n"
            report += f"Sharpe Ratio: {sharpe:.3f}\n"
            report += f"Risk of Ruin: {(100 - win_rate):.1f}%\n"
            report += f"Maximum Drawdown: {abs(min_profit):.2f} Sigils\n\n"
            
            # Recommendations
            report += "RECOMMENDATIONS\n"
            report += "-" * 50 + "\n"
            
            if avg_profit > 0:
                report += "✓ Strategy is profitable (Positive Expected Value)\n"
            else:
                report += "⚠ Strategy is not profitable (Negative Expected Value)\n"
            
            if win_rate > 50:
                report += "✓ Good win rate\n"
            else:
                report += "⚠ Win rate below 50%\n"
            
            if std_profit and std_profit > abs(avg_profit) * 2:
                report += "⚠ High volatility detected\n"
        
        conn.close()
        return report
    
    def backup_database(self):
        """Create backup of database"""
        import shutil
        import os
        
        backup_dir = "backups"
        if not os.path.exists(backup_dir):
            os.makedirs(backup_dir)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(backup_dir, f"game_backup_{timestamp}.db")
        
        shutil.copy2(self.db_path, backup_file)
        
        messagebox.showinfo("Backup Complete", 
                          f"Database backed up to:\n{backup_file}")
        self.status_var.set(f"Database backed up: {backup_file}")

# Main application
def main():
    """Launch the application"""
    root = tk.Tk()
    app = GameResultLogger(root)
    root.mainloop()

if __name__ == "__main__":
    print("Starting Bomb Game Result Logger with Advanced Analytics...")
    main()