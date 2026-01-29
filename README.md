# INFICON_STM-2_remote_monitor
- INFICON STM-2 USB 薄膜蒸着レート/膜厚モニター の.logファイルを遠隔監視するためのシステム。（INFICON非公式）  
- **InfluxDB** と **Grafana** を用いてリアルタイムに可視化します。  
- このリポジトリには、すぐに利用できる Grafana ダッシュボード（JSON）が含まれています。  
 
![外部向け説明資料](https://github.com/user-attachments/assets/eb5fce0c-8dbf-4847-b3d2-5c2d21164ab5)
本システムで使用する物性値について、正確性を保証するものではありません。利用により生じたいかなる結果についても、作者は責任を負いません。  
電子ビーム蒸着装置に取り付けられたSTM-2を想定して作成。  

## ✨ 特長

- STM-2 の膜厚・成膜レート・周波数をリアルタイム監視
- 目標膜厚の 80% を超えた際に自動アラート
- Grafana ダッシュボードをそのままインポート可能
- 研究室の自動化・遠隔監視に適したシンプルな構成


## STM-2接続パソコンの準備：
Windowsマシンを想定しています。  
Windows Defender ファイアウォールに受信規則を追加してポート3000を開放する。  
固定IPアドレスを設定する。あらかじめネットワーク管理者に確認することをおすすめします。  
STM-2を接続しているパソコンに、Pythonをインストール。  
コマンドプロンプトで下記の三つのコマンドを実行して必要なライブラリをインストールする。  

pip install influxdb  
pip install customtkinter  
pip install tkinterdnd2  

InfluxDBをインストール。  
STM-2 のログスクリプトとの互換性のため、InfluxDB v1.x を推奨します。  

Grafanaをインストール。  
"STM-2-1769471897840.json" をインポートして各種設定を完了させる。  
- Grafana → Dashboards → Import  
- JSON Upload または JSON を貼り付け  
- Data source を InfluxDB に設定  


## 動作手順：
### STM-2専用ソフトウェア
INFICON公式STM-2専用ソフトウェアを起動。必要な設定をして記録start。
### InfluxDB
InfluxDBのフォルダに移動し、Shiftキーを押しながら右クリックし、“ここでコマンドウィンドウを開く”メニューを選択。  
コマンドプロンプトで、".\influxd"を入力し、Influxdb.exeを実行する。
### Python
コードを実行する。  
GUIで蒸着材料を選択すると、自動で密度とZ-ratioがGUIに入力される。  
目標厚さを nm で指定する。  
参照ボタンをクリックし、STM-2のログファイルを選択する。STM-2のログファイルが入っているフォルダから現在記録中のログファイルを選ぶ。
### Grafana
遠隔監視したいパソコンのwebブラウザを開き、下記URLを開く。  
http://（固定IPアドレス）:3000  
