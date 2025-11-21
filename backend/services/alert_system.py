"""
Alert System - Manages security alerts and notifications
"""

import logging
from datetime import datetime
from database.db import Database

logger = logging.getLogger(__name__)


class AlertSystem:
    def __init__(self):
        """Initialize alert system"""
        self.db = Database()
        
        # Alert severity levels
        self.severity_levels = {
            'critical': 4,
            'high': 3,
            'medium': 2,
            'low': 1
        }
        
        # Alert type configurations
        self.alert_configs = {
            'crowd_formation': {
                'default_severity': 'medium',
                'notification': True,
                'description_template': 'Crowd detected: {people_count} people'
            },
            'abandoned_object': {
                'default_severity': 'high',
                'notification': True,
                'description_template': 'Unattended {object_type} detected'
            },
            'suspicious_object': {
                'default_severity': 'critical',
                'notification': True,
                'description_template': '{object_type} detected with {confidence}% confidence'
            },
            'intrusion': {
                'default_severity': 'critical',
                'notification': True,
                'description_template': 'Unauthorized entry detected'
            },
            'loitering': {
                'default_severity': 'medium',
                'notification': True,
                'description_template': 'Person loitering for extended period'
            },
            'restricted_area': {
                'default_severity': 'high',
                'notification': True,
                'description_template': 'Access to restricted area detected'
            }
        }
        
        logger.info("Alert system initialized")
    
    def is_active(self):
        """Check if alert system is active"""
        return True
    
    def create_alert(self, anomaly_data, video_id, camera_id):
        """
        Create an alert from anomaly detection
        
        Args:
            anomaly_data: Dict containing anomaly information
            video_id: ID of the video where anomaly was detected
            camera_id: ID of the camera
        
        Returns:
            int: Alert ID
        """
        try:
            alert_type = anomaly_data['type']
            
            # Get configuration for this alert type
            config = self.alert_configs.get(alert_type, {})
            
            # Determine severity
            severity = anomaly_data.get('severity', config.get('default_severity', 'medium'))
            
            # Generate description
            description = self._generate_description(alert_type, anomaly_data, config)
            
            # Prepare alert data
            alert_data = {
                'video_id': video_id,
                'camera_id': camera_id,
                'alert_type': alert_type,
                'severity': severity,
                'timestamp': anomaly_data.get('timestamp', datetime.now().timestamp()),
                'description': description,
                'metadata': anomaly_data.get('metadata', {})
            }
            
            # Save to database
            alert_id = self.db.add_alert(alert_data)
            
            logger.info(f"Alert created: ID={alert_id}, Type={alert_type}, Severity={severity}")
            
            # Send notification if configured
            if config.get('notification', False):
                self._send_notification(alert_data)
            
            return alert_id
        
        except Exception as e:
            logger.error(f"Error creating alert: {str(e)}")
            return None
    
    def _generate_description(self, alert_type, anomaly_data, config):
        """Generate human-readable alert description"""
        template = config.get('description_template', 'Security anomaly detected')
        
        try:
            metadata = anomaly_data.get('metadata', {})
            
            # Replace placeholders with actual data
            description = template
            for key, value in metadata.items():
                placeholder = '{' + key + '}'
                if placeholder in description:
                    description = description.replace(placeholder, str(value))
            
            return description
        
        except Exception as e:
            logger.error(f"Error generating description: {str(e)}")
            return anomaly_data.get('description', 'Security anomaly detected')
    
    def _send_notification(self, alert_data):
        """
        Send notification for alert
        In production, this would integrate with:
        - Email services (SMTP, SendGrid)
        - SMS services (Twilio)
        - Push notifications (Firebase, OneSignal)
        - Slack/Teams webhooks
        """
        logger.info(f"Notification sent for alert: {alert_data['alert_type']} - {alert_data['severity']}")
        
        # Placeholder for actual notification implementation
        pass
    
    def get_alert_statistics(self, start_date=None, end_date=None):
        """
        Get alert statistics for a date range
        
        Args:
            start_date: Start date (datetime or ISO string)
            end_date: End date (datetime or ISO string)
        
        Returns:
            dict: Alert statistics
        """
        try:
            alerts = self.db.get_alerts(limit=1000)  # Get all recent alerts
            
            # Count by severity
            severity_counts = {
                'critical': 0,
                'high': 0,
                'medium': 0,
                'low': 0
            }
            
            # Count by type
            type_counts = {}
            
            for alert in alerts:
                # Count by severity
                severity = alert.get('severity', 'low')
                if severity in severity_counts:
                    severity_counts[severity] += 1
                
                # Count by type
                alert_type = alert.get('alert_type', 'unknown')
                type_counts[alert_type] = type_counts.get(alert_type, 0) + 1
            
            return {
                'total_alerts': len(alerts),
                'by_severity': severity_counts,
                'by_type': type_counts,
                'critical_alerts': severity_counts['critical'],
                'resolved_alerts': sum(1 for a in alerts if a.get('status') == 'resolved')
            }
        
        except Exception as e:
            logger.error(f"Error getting alert statistics: {str(e)}")
            return {}
    
    def escalate_alert(self, alert_id, new_severity):
        """
        Escalate alert to higher severity
        
        Args:
            alert_id: ID of alert to escalate
            new_severity: New severity level
        """
        try:
            # Get current alert
            alert = self.db.get_alert_by_id(alert_id)
            
            if not alert:
                logger.error(f"Alert {alert_id} not found")
                return False
            
            current_severity = alert.get('severity', 'low')
            
            # Check if escalation is valid
            if self.severity_levels[new_severity] <= self.severity_levels[current_severity]:
                logger.warning(f"Cannot escalate to same or lower severity")
                return False
            
            # Update alert
            self.db.update_alert_status(
                alert_id,
                status='escalated',
                notes=f'Escalated from {current_severity} to {new_severity}'
            )
            
            logger.info(f"Alert {alert_id} escalated from {current_severity} to {new_severity}")
            
            # Send urgent notification
            self._send_notification({
                **alert,
                'severity': new_severity,
                'escalated': True
            })
            
            return True
        
        except Exception as e:
            logger.error(f"Error escalating alert: {str(e)}")
            return False
    
    def resolve_alert(self, alert_id, notes=''):
        """
        Mark alert as resolved
        
        Args:
            alert_id: ID of alert to resolve
            notes: Resolution notes
        """
        try:
            self.db.update_alert_status(alert_id, 'resolved', notes)
            logger.info(f"Alert {alert_id} resolved")
            return True
        
        except Exception as e:
            logger.error(f"Error resolving alert: {str(e)}")
            return False
    
    def acknowledge_alert(self, alert_id, notes=''):
        """
        Acknowledge alert (user has seen it)
        
        Args:
            alert_id: ID of alert to acknowledge
            notes: Acknowledgment notes
        """
        try:
            self.db.update_alert_status(alert_id, 'acknowledged', notes)
            logger.info(f"Alert {alert_id} acknowledged")
            return True
        
        except Exception as e:
            logger.error(f"Error acknowledging alert: {str(e)}")
            return False
    
    def get_alert_summary(self):
        """Get summary of recent alerts for dashboard"""
        try:
            alerts = self.db.get_alerts(limit=100)
            
            # Get today's stats
            today = datetime.now().date()
            today_alerts = [a for a in alerts if a.get('created_at', '').startswith(str(today))]
            
            return {
                'total_today': len(today_alerts),
                'critical_today': sum(1 for a in today_alerts if a.get('severity') == 'critical'),
                'unresolved': sum(1 for a in alerts if a.get('status') == 'new'),
                'recent_alerts': alerts[:5]  # 5 most recent
            }
        
        except Exception as e:
            logger.error(f"Error getting alert summary: {str(e)}")
            return {}


# Example usage
if __name__ == "__main__":
    alert_system = AlertSystem()
    
    # Test creating an alert
    test_anomaly = {
        'type': 'crowd_formation',
        'severity': 'medium',
        'timestamp': datetime.now().timestamp(),
        'description': 'Test alert',
        'metadata': {
            'people_count': 8
        }
    }
    
    alert_id = alert_system.create_alert(test_anomaly, video_id=1, camera_id=1)
    print(f"Created alert: {alert_id}")
    
    # Get statistics
    stats = alert_system.get_alert_statistics()
    print(f"Alert statistics: {stats}")