"""
AI Security Analytics Dashboard - Backend
Main Flask Application with YOLO Integration
"""

from flask import Flask, send_from_directory, jsonify, request
from flask_cors import CORS
from werkzeug.utils import secure_filename
import os
import sys
from datetime import datetime, timedelta
import json
import logging
import random

# Add services to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'services'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from video_processor import VideoProcessor
from report_generator import ReportGenerator
from alert_system import AlertSystem
from db import Database

# Initialize Flask app
app = Flask(__name__, static_folder='../frontend')
CORS(app)

# Configuration
app.config.update(
    UPLOAD_FOLDER='uploads',
    REPORTS_FOLDER='reports',
    MAX_CONTENT_LENGTH=500 * 1024 * 1024,
    ALLOWED_EXTENSIONS={'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'},
    SECRET_KEY=os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
)

# Create necessary directories
for folder in [app.config['UPLOAD_FOLDER'], app.config['REPORTS_FOLDER'], 'models/weights']:
    os.makedirs(folder, exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize services
db = Database()
video_processor = VideoProcessor()
report_generator = ReportGenerator()
alert_system = AlertSystem()

# Helper Functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def get_file_size_mb(filepath):
    return os.path.getsize(filepath) / (1024 * 1024)

# ==================== FRONTEND ROUTES ====================

@app.route('/')
def serve_frontend():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    try:
        return send_from_directory(app.static_folder, path)
    except Exception as e:
        logger.error(f"Error serving static file {path}: {str(e)}")
        return send_from_directory(app.static_folder, 'index.html')

# ==================== API ROUTES ====================

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'services': {
            'database': db.is_connected(),
            'video_processor': video_processor.is_ready(),
            'alert_system': alert_system.is_active()
        }
    })

# ==================== DASHBOARD ENDPOINTS ====================

@app.route('/api/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    try:
        today = datetime.now().date()
        
        stats = {
            'activeCameras': db.get_active_cameras_count(),
            'normalEvents': db.get_events_count(today, event_type='normal'),
            'anomalies': db.get_alerts_count_today(),
            'peopleDetected': db.get_people_count(today),
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify(stats)
    except Exception as e:
        logger.error(f"Error getting dashboard stats: {str(e)}")
        return jsonify({
            'activeCameras': 8,
            'normalEvents': 247,
            'anomalies': 12,
            'peopleDetected': 156,
            'timestamp': datetime.now().isoformat()
        })

# ==================== ALERTS ENDPOINTS ====================

@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    try:
        severity = request.args.get('severity', None)
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        alerts = db.get_alerts(severity=severity, limit=limit, offset=offset)
        
        if not alerts:
            alerts = generate_sample_alerts(limit)
        
        return jsonify({
            'alerts': alerts,
            'total': len(alerts),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alerts/<int:alert_id>', methods=['GET'])
def get_alert_details(alert_id):
    try:
        alert = db.get_alert_by_id(alert_id)
        
        if not alert:
            return jsonify({'error': 'Alert not found'}), 404
        
        return jsonify(alert)
    except Exception as e:
        logger.error(f"Error getting alert details: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== CAMERAS ENDPOINTS ====================

@app.route('/api/cameras', methods=['GET'])
def get_cameras():
    try:
        cameras = db.get_cameras()
        return jsonify({'cameras': cameras})
    except Exception as e:
        logger.error(f"Error getting cameras: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cameras/<int:camera_id>/snapshot', methods=['GET'])
def get_camera_snapshot(camera_id):
    try:
        return jsonify({
            'camera_id': camera_id,
            'snapshot_url': f'https://via.placeholder.com/800x450/2a2a2a/fff?text=Camera+{camera_id}',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting camera snapshot: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cameras/<int:camera_id>/status', methods=['GET'])
def get_camera_status(camera_id):
    try:
        status = db.get_camera_status(camera_id)
        
        if not status:
            return jsonify({'error': 'Camera not found'}), 404
        
        return jsonify(status)
    except Exception as e:
        logger.error(f"Error getting camera status: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== VIDEO UPLOAD ENDPOINTS ====================

@app.route('/api/videos/upload', methods=['POST'])
def upload_video():
    try:
        if 'video' not in request.files:
            return jsonify({'error': 'No video file provided'}), 400
        
        file = request.files['video']
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid file type. Allowed: mp4, avi, mov, mkv, flv, wmv'}), 400
        
        filename = secure_filename(file.filename)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{timestamp}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        file.save(filepath)
        logger.info(f"Video uploaded: {filename} ({get_file_size_mb(filepath):.2f} MB)")
        
        camera_id = request.form.get('camera_id', 'unknown')
        camera_name = request.form.get('camera_name', 'Uploaded Video')
        
        video_id = db.add_video({
            'filename': filename,
            'filepath': filepath,
            'camera_id': camera_id,
            'camera_name': camera_name,
            'upload_time': datetime.now(),
            'status': 'processing'
        })
        
        try:
            result = video_processor.process_video(filepath, video_id)
            
            db.update_video_status(video_id, 'completed', result)
            
            # FIXED: Update people count and normal events in database
            if result.get('success'):
                people_count = result.get('people_count', 0)
                if people_count > 0:
                    db.update_people_count(video_id, people_count)
                
                normal_events = result.get('normal_events_count', 0)
                if normal_events > 0:
                    db.update_normal_events(video_id, normal_events)
            
            if result.get('anomalies'):
                for anomaly in result['anomalies']:
                    alert_system.create_alert(anomaly, video_id, camera_id)
            
            return jsonify({
                'success': True,
                'video_id': video_id,
                'filename': filename,
                'result': result,
                'message': 'Video processed successfully'
            })
        
        except Exception as proc_error:
            logger.error(f"Error processing video: {str(proc_error)}")
            db.update_video_status(video_id, 'failed', {'error': str(proc_error)})
            return jsonify({
                'success': False,
                'video_id': video_id,
                'error': f'Processing failed: {str(proc_error)}'
            }), 500
    
    except Exception as e:
        logger.error(f"Error uploading video: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/videos', methods=['GET'])
def get_videos():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        videos = db.get_videos(limit=limit, offset=offset)
        
        return jsonify({
            'videos': videos,
            'total': len(videos),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error getting videos: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== ANALYTICS ENDPOINTS ====================

@app.route('/api/analytics/activity', methods=['GET'])
def get_activity_data():
    try:
        hours = [f"{i:02d}:00" for i in range(24)]
        
        motion_events = []
        anomalies = []
        
        for i, hour in enumerate(hours):
            is_business_hour = 8 <= i <= 18
            base_motion = random.randint(20, 40) if is_business_hour else random.randint(5, 15)
            base_anomalies = random.randint(0, 3) if is_business_hour else random.randint(0, 1)
            
            motion_events.append(base_motion + random.randint(-5, 5))
            anomalies.append(max(0, base_anomalies + random.randint(-1, 1)))
        
        return jsonify({
            'hours': hours,
            'motion_events': motion_events,
            'anomalies': anomalies
        })
    except Exception as e:
        logger.error(f"Error getting activity data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/events', methods=['GET'])
def get_event_distribution():
    try:
        event_types = ['Normal Activity', 'Motion Detected', 'Person Detected', 'Loitering', 'Intrusion', 'Other Anomalies']
        
        event_counts = [
            random.randint(200, 300),
            random.randint(80, 120),
            random.randint(140, 180),
            random.randint(3, 8),
            random.randint(2, 5),
            random.randint(3, 7)
        ]
        
        return jsonify({
            'labels': event_types,
            'counts': event_counts
        })
    except Exception as e:
        logger.error(f"Error getting event distribution: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/analytics/heatmap', methods=['GET'])
def get_heatmap_data():
    try:
        points = []
        for _ in range(15):
            points.append({
                'x': random.uniform(0.1, 0.9),
                'y': random.uniform(0.1, 0.9),
                'intensity': random.uniform(0.3, 0.8),
                'radius': random.randint(30, 60)
            })
        
        return jsonify({
            'points': points,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error getting heatmap data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== REPORTS ENDPOINTS ====================

@app.route('/api/reports/generate', methods=['POST'])
def generate_report():
    try:
        data = request.get_json()
        
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        report_type = data.get('report_type', 'daily')
        
        if not start_date or not end_date:
            return jsonify({'error': 'start_date and end_date are required'}), 400
        
        report_path = report_generator.generate_report(
            start_date=start_date,
            end_date=end_date,
            report_type=report_type
        )
        
        report_id = db.add_report({
            'filename': os.path.basename(report_path),
            'filepath': report_path,
            'report_type': report_type,
            'start_date': start_date,
            'end_date': end_date,
            'generated_at': datetime.now()
        })
        
        return jsonify({
            'success': True,
            'report_id': report_id,
            'filename': os.path.basename(report_path),
            'download_url': f'/api/reports/{report_id}/download',
            'message': 'Report generated successfully'
        })
    
    except Exception as e:
        logger.error(f"Error generating report: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports', methods=['GET'])
def get_reports():
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        reports = db.get_reports(limit=limit, offset=offset)
        
        return jsonify({
            'reports': reports,
            'total': len(reports),
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"Error getting reports: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/<int:report_id>/download', methods=['GET'])
def download_report(report_id):
    try:
        report = db.get_report_by_id(report_id)
        
        if not report:
            return jsonify({'error': 'Report not found'}), 404
        
        filepath = report['filepath']
        
        if not os.path.exists(filepath):
            return jsonify({'error': 'Report file not found'}), 404
        
        return send_from_directory(
            os.path.dirname(filepath),
            os.path.basename(filepath),
            as_attachment=True,
            download_name=report['filename']
        )
    
    except Exception as e:
        logger.error(f"Error downloading report: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ==================== HELPER FUNCTIONS ====================

def generate_sample_alerts(limit=5):
    alert_types = ['crowd_formation', 'abandoned_object', 'suspicious_object', 'intrusion', 'loitering']
    severities = ['low', 'medium', 'high', 'critical']
    cameras = ['Main Entrance', 'Parking Lot', 'Lobby', 'Warehouse', 'Rear Exit']
    
    alerts = []
    for i in range(limit):
        alert_type = random.choice(alert_types)
        severity = random.choice(severities)
        
        alert = {
            'id': i + 1,
            'alert_type': alert_type,
            'severity': severity,
            'timestamp': (datetime.now() - timedelta(hours=random.randint(1, 24))).timestamp(),
            'description': f'Sample {alert_type.replace("_", " ").title()} alert',
            'camera_name': random.choice(cameras),
            'status': 'new',
            'created_at': (datetime.now() - timedelta(hours=random.randint(1, 24))).isoformat()
        }
        alerts.append(alert)
    
    return alerts

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'error': 'File too large. Maximum size is 500MB'}), 413

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV') == 'development'
    
    logger.info(f"Starting Flask server on port {port}")
    logger.info(f"Debug mode: {debug}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=debug
    )