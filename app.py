from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import random
import math
import os

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{os.path.join(BASE_DIR, "water.db")}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# 数据模型
class Station(db.Model):
    __tablename__ = 'station'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))
    river = db.Column(db.String(50))
    warning_level = db.Column(db.Float)
    city = db.Column(db.String(50))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)


class WaterLevel(db.Model):
    __tablename__ = 'water_level'
    id = db.Column(db.Integer, primary_key=True)
    station_id = db.Column(db.Integer, db.ForeignKey('station.id'))
    date = db.Column(db.Date)
    level = db.Column(db.Float)
    remark = db.Column(db.String(100))


# 创建数据库和初始数据
with app.app_context():
    db.create_all()
    
    if Station.query.count() == 0:
        stations = [
            Station(id=1, name='刘家坝水文站', river='清溪河', warning_level=3.2, city='汉江市', latitude=30.52, longitude=114.28),
            Station(id=2, name='清溪桥下游站', river='清溪河', warning_level=3.15, city='汉江市', latitude=30.48, longitude=114.35),
            Station(id=3, name='石门坎水文站', river='清溪河', warning_level=3.3, city='临水县', latitude=30.42, longitude=114.42),
            Station(id=4, name='月亮湾水位站', river='玉带河', warning_level=2.8, city='青川县', latitude=30.38, longitude=114.50),
            Station(id=5, name='东风渠进水闸', river='东风渠', warning_level=2.5, city='平原区', latitude=30.33, longitude=114.58),
        ]
        db.session.add_all(stations)
        
        # 生成模拟水位数据
        end_date = datetime.now().date()
        for station in stations:
            for i in range(60):
                date = end_date - timedelta(days=i)
                level = station.warning_level - 0.3 + 0.2 * math.sin(i / 10) + random.uniform(-0.1, 0.1)
                level = round(max(2.0, min(3.8, level)), 2)
                db.session.add(WaterLevel(station_id=station.id, date=date, level=level, remark=''))
        db.session.commit()


@app.route('/')
def index():
    return render_template('day20_full_system.html')


@app.route('/full_system')
def full_system():
    return render_template('day20_full_system.html')


@app.route('/api/stations')
def api_stations():
    stations = Station.query.all()
    return jsonify([{
        'id': s.id,
        'name': s.name,
        'river': s.river,
        'warning_level': s.warning_level,
        'city': s.city,
        'latitude': s.latitude,
        'longitude': s.longitude
    } for s in stations])


@app.route('/api/water_data')
def api_water_data():
    station_id = request.args.get('station_id', '')
    start_date = request.args.get('start_date', '')
    end_date = request.args.get('end_date', '')
    
    query = WaterLevel.query
    if station_id and station_id != 'all':
        query = query.filter(WaterLevel.station_id == int(station_id))
    if start_date:
        query = query.filter(WaterLevel.date >= datetime.strptime(start_date, '%Y-%m-%d'))
    if end_date:
        query = query.filter(WaterLevel.date <= datetime.strptime(end_date, '%Y-%m-%d'))
    
    records = query.order_by(WaterLevel.date.desc()).limit(100).all()
    records.reverse()
    
    data = []
    for r in records:
        station = Station.query.get(r.station_id)
        data.append({
            'date': r.date.strftime('%Y-%m-%d'),
            'station_name': station.name if station else '',
            'level': r.level,
            'warning_level': station.warning_level if station else 0
        })
    return jsonify(data)


@app.route('/api/chart_data')
def api_chart_data():
    station_id = request.args.get('station_id', '')
    days = int(request.args.get('days', 30))
    
    if station_id and station_id != 'all':
        records = WaterLevel.query.filter_by(station_id=int(station_id)).order_by(WaterLevel.date.desc()).limit(days).all()
        records.reverse()
        station = Station.query.get(int(station_id))
        return jsonify({
            'type': 'single',
            'station_name': station.name,
            'warning_level': station.warning_level,
            'dates': [r.date.strftime('%m-%d') for r in records],
            'levels': [r.level for r in records]
        })
    else:
        stations = Station.query.all()
        series = []
        for s in stations:
            records = WaterLevel.query.filter_by(station_id=s.id).order_by(WaterLevel.date.desc()).limit(days).all()
            records.reverse()
            if records:
                series.append({
                    'name': s.name,
                    'dates': [r.date.strftime('%m-%d') for r in records],
                    'levels': [r.level for r in records]
                })
        return jsonify({'type': 'multi', 'series': series})


if __name__ == '__main__':
    app.run(debug=True)
