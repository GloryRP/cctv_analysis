"""
Database Module - SQLite Database Management
Handles all database operations for the security system
"""

import sqlite3
import json
from datetime import datetime, timedelta
from contextlib import contextmanager
import logging
import os

logger = logging.getLogger(__name__)


class Database:
    def __init__(self, db_path='security_system.db'):
        """Initialize database connection"""
        self.db_path = db_path
        self._create_tables()
        logger.info(f"Database initialized: {db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {str(e)}")
            raise
        finally:
            conn.close()
    
    def _create_tables(self):
        """Create all necessary database tables"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Cameras table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS cameras (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    location TEXT,
                    status TEXT DEFAULT 'online',
                    ip_address TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Videos table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS videos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    camera_id INTEGER,
                    camera_name TEXT,
                    upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    duration REAL,
                    fps INTEGER,
                    total_frames INTEGER,
                    status TEXT DEFAULT 'pending',
                    results TEXT,
                    FOREIGN KEY (camera_id) REFERENCES cameras(id)
                )
            ''')
            
            # Detections table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS detections (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    timestamp REAL NOT NULL,
                    object_class TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    bbox TEXT,
                    frame_number INTEGER,
                    FOREIGN KEY (video_id) REFERENCES videos(id)
                )
            ''')
            
            # Alerts/Anomalies table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER,
                    camera_id INTEGER,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    description TEXT,
                    metadata TEXT,
                    status TEXT DEFAULT 'new',
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos(id),
                    FOREIGN KEY (camera_id) REFERENCES cameras(id)
                )
            ''')
            
            # Events table (motion, people detected, etc.)
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    video_id INTEGER NOT NULL,
                    camera_id INTEGER,
                    event_type TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (video_id) REFERENCES videos(id),
                    FOREIGN KEY (camera_id) REFERENCES cameras(id)
                )
            ''')
            
            # Reports table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    filepath TEXT NOT NULL,
                    report_type TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Initialize default cameras
            self._initialize_default_cameras(cursor)
            
            logger.info("Database tables created successfully")
    
    def _initialize_default_cameras(self, cursor):
        """Initialize default cameras if none exist"""
        cursor.execute("SELECT COUNT(*) as count FROM cameras")
        count = cursor.fetchone()['count']
        
        if count == 0:
            default_cameras = [
                ('Main Entrance', 'Building A - Front', 'online', '192.168.1.101'),
                ('Parking Lot', 'Outdoor - West Side', 'online', '192.168.1.102'),
                ('Loading Dock', 'Building B - Rear', 'online', '192.168.1.103'),
                ('Rear Exit', 'Building A - Back', 'online', '192.168.1.104'),
                ('Lobby', 'Building A - Ground Floor', 'online', '192.168.1.105'),
                ('Warehouse', 'Building B - Main Area', 'online', '192.168.1.106'),
                ('Side Gate', 'Perimeter - East', 'online', '192.168.1.107'),
                ('Rooftop', 'Building A - Top Floor', 'online', '192.168.1.108')
            ]
            
            cursor.executemany(
                'INSERT INTO cameras (name, location, status, ip_address) VALUES (?, ?, ?, ?)',
                default_cameras
            )
            logger.info(f"Initialized {len(default_cameras)} default cameras")
    
    def is_connected(self):
        """Check database connectivity"""
        try:
            with self.get_connection() as conn:
                conn.execute("SELECT 1")
            return True
        except:
            return False
    
    # ========== CAMERAS ==========
    
    def get_cameras(self):
        """Get all cameras"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cameras ORDER BY id')
            return [dict(row) for row in cursor.fetchall()]
    
    def get_active_cameras_count(self):
        """Get count of active cameras"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM cameras WHERE status = 'online'")
            return cursor.fetchone()['count']
    
    def get_camera_status(self, camera_id):
        """Get status of a specific camera"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM cameras WHERE id = ?', (camera_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========== VIDEOS ==========
    
    def add_video(self, video_data):
        """Add new video to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO videos (filename, filepath, camera_id, camera_name, upload_time, status)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                video_data['filename'],
                video_data['filepath'],
                video_data.get('camera_id'),
                video_data.get('camera_name'),
                video_data['upload_time'],
                video_data['status']
            ))
            return cursor.lastrowid
    
    def update_video_status(self, video_id, status, results=None):
        """Update video processing status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if results:
                cursor.execute('''
                    UPDATE videos 
                    SET status = ?, 
                        results = ?,
                        duration = ?,
                        fps = ?,
                        total_frames = ?
                    WHERE id = ?
                ''', (
                    status,
                    json.dumps(results),
                    results.get('duration'),
                    results.get('fps'),
                    results.get('total_frames'),
                    video_id
                ))
            else:
                cursor.execute('UPDATE videos SET status = ? WHERE id = ?', (status, video_id))
    
    def get_videos(self, limit=50, offset=0):
        """Get list of videos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM videos 
                ORDER BY upload_time DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_video_results(self, video_id):
        """Get processing results for a video"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM videos WHERE id = ?', (video_id,))
            row = cursor.fetchone()
            if row:
                video = dict(row)
                if video['results']:
                    video['results'] = json.loads(video['results'])
                return video
            return None
    
    # ========== ALERTS ==========
    
    def add_alert(self, alert_data):
        """Add new alert to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts 
                (video_id, camera_id, alert_type, severity, timestamp, description, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                alert_data.get('video_id'),
                alert_data.get('camera_id'),
                alert_data['alert_type'],
                alert_data['severity'],
                alert_data['timestamp'],
                alert_data.get('description'),
                json.dumps(alert_data.get('metadata', {}))
            ))
            return cursor.lastrowid
    
    def get_alerts(self, severity=None, limit=50, offset=0):
        """Get alerts with optional filtering"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if severity:
                cursor.execute('''
                    SELECT a.*, c.name as camera_name 
                    FROM alerts a
                    LEFT JOIN cameras c ON a.camera_id = c.id
                    WHERE a.severity = ?
                    ORDER BY a.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (severity, limit, offset))
            else:
                cursor.execute('''
                    SELECT a.*, c.name as camera_name 
                    FROM alerts a
                    LEFT JOIN cameras c ON a.camera_id = c.id
                    ORDER BY a.created_at DESC
                    LIMIT ? OFFSET ?
                ''', (limit, offset))
            
            alerts = []
            for row in cursor.fetchall():
                alert = dict(row)
                if alert['metadata']:
                    alert['metadata'] = json.loads(alert['metadata'])
                alerts.append(alert)
            
            return alerts
    
    def get_alert_by_id(self, alert_id):
        """Get specific alert by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*, c.name as camera_name, v.filename as video_filename
                FROM alerts a
                LEFT JOIN cameras c ON a.camera_id = c.id
                LEFT JOIN videos v ON a.video_id = v.id
                WHERE a.id = ?
            ''', (alert_id,))
            row = cursor.fetchone()
            
            if row:
                alert = dict(row)
                if alert['metadata']:
                    alert['metadata'] = json.loads(alert['metadata'])
                return alert
            return None
    
    def update_alert_status(self, alert_id, status, notes=''):
        """Update alert status"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE alerts 
                SET status = ?, notes = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (status, notes, alert_id))
    
    def get_alerts_count_today(self):
        """Get count of alerts for today"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            today = datetime.now().date()
            cursor.execute("SELECT COUNT(*) as count FROM alerts WHERE DATE(created_at) = ?", (str(today),))
            return cursor.fetchone()['count']
    
    def get_recent_alerts(self, limit=5):
        """Get recent alerts for dashboard"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*, c.name as camera_name 
                FROM alerts a
                LEFT JOIN cameras c ON a.camera_id = c.id
                ORDER BY a.created_at DESC
                LIMIT ?
            ''', (limit,))
            
            alerts = []
            for row in cursor.fetchall():
                alert = dict(row)
                if alert['metadata']:
                    alert['metadata'] = json.loads(alert['metadata'])
                alerts.append(alert)
            
            return alerts
    
    # ========== EVENTS ==========
    
    def add_event(self, event_data):
        """Add event to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO events (video_id, camera_id, event_type, timestamp, data)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                event_data['video_id'],
                event_data.get('camera_id'),
                event_data['event_type'],
                event_data['timestamp'],
                json.dumps(event_data.get('data', {}))
            ))
            return cursor.lastrowid
    
    def get_events_count(self, date, event_type=None):
        """Get count of events for a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Convert date to timestamp range
            date_obj = datetime.fromisoformat(str(date))
            start_ts = date_obj.timestamp()
            end_ts = (date_obj + timedelta(days=1)).timestamp()
            
            if event_type:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM events 
                    WHERE timestamp >= ? AND timestamp < ? AND event_type = ?
                ''', (start_ts, end_ts, event_type))
            else:
                cursor.execute('''
                    SELECT COUNT(*) as count FROM events 
                    WHERE timestamp >= ? AND timestamp < ?
                ''', (start_ts, end_ts))
            
            return cursor.fetchone()['count']
    
    def get_people_count(self, date):
        """Get total people detected on a specific date"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT COUNT(*) as count FROM detections d
                JOIN videos v ON d.video_id = v.id
                WHERE DATE(v.upload_time) = ? AND d.object_class = 'person'
            ''', (str(date),))
            
            result = cursor.fetchone()
            return result['count'] if result else 0
    
    # ========== REPORTS ==========
    
    def add_report(self, report_data):
        """Add generated report to database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reports (filename, filepath, report_type, start_date, end_date, generated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                report_data['filename'],
                report_data['filepath'],
                report_data['report_type'],
                report_data['start_date'],
                report_data['end_date'],
                report_data['generated_at']
            ))
            return cursor.lastrowid
    
    def get_reports(self, limit=50, offset=0):
        """Get list of reports"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM reports 
                ORDER BY generated_at DESC 
                LIMIT ? OFFSET ?
            ''', (limit, offset))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_report_by_id(self, report_id):
        """Get specific report by ID"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM reports WHERE id = ?', (report_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    # ========== ANALYTICS ==========
    
    def get_activity_timeline(self, hours=24):
        """Get activity timeline for charts"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get timestamp for X hours ago
            cutoff_time = datetime.now() - timedelta(hours=hours)
            cutoff_ts = cutoff_time.timestamp()
            
            # Get motion events by hour
            cursor.execute('''
                SELECT 
                    strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
                    COUNT(*) as count
                FROM events
                WHERE timestamp >= ? AND event_type = 'motion'
                GROUP BY hour
                ORDER BY hour
            ''', (cutoff_ts,))
            
            motion_data = {row['hour']: row['count'] for row in cursor.fetchall()}
            
            # Get anomalies by hour
            cursor.execute('''
                SELECT 
                    strftime('%H', datetime(timestamp, 'unixepoch')) as hour,
                    COUNT(*) as count
                FROM alerts
                WHERE timestamp >= ?
                GROUP BY hour
                ORDER BY hour
            ''', (cutoff_ts,))
            
            anomaly_data = {row['hour']: row['count'] for row in cursor.fetchall()}
            
            return {
                'motion': motion_data,
                'anomalies': anomaly_data
            }
    
    def get_event_distribution(self, date):
        """Get event distribution for pie chart"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT event_type, COUNT(*) as count
                FROM events
                WHERE DATE(created_at) = ?
                GROUP BY event_type
            ''', (str(date),))
            
            return {row['event_type']: row['count'] for row in cursor.fetchall()}
    
    def get_heatmap_data(self, camera_id=None, date=None):
        """Get heatmap data for visualization"""
        return {
            'points': [],
            'camera_id': camera_id,
            'date': date
        }
    
    # ========== NEW METHODS FOR VIDEO PROCESSING ==========
    
    def update_people_count(self, video_id, people_count):
        """Update people count from video processing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Add detection records for people
            for i in range(people_count):
                cursor.execute('''
                    INSERT INTO detections (video_id, timestamp, object_class, confidence, bbox, frame_number)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    video_id,
                    datetime.now().timestamp(),
                    'person',
                    0.85,
                    json.dumps([0, 0, 1, 1]),
                    1
                ))

    def update_normal_events(self, video_id, event_count):
        """Update normal events count from video processing"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            for i in range(event_count):
                cursor.execute('''
                    INSERT INTO events (video_id, event_type, timestamp, data)
                    VALUES (?, ?, ?, ?)
                ''', (
                    video_id,
                    'motion',
                    datetime.now().timestamp(),
                    json.dumps({'intensity': 0.5})
                ))


if __name__ == "__main__":
    db = Database()
    print("Active cameras:", db.get_active_cameras_count())
    print("Cameras:", db.get_cameras())
    print("Database connected:", db.is_connected())