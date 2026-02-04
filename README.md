# INFICON_STM-2_remote_monitor
- INFICON STM-2 USB 薄膜蒸着レート/膜厚モニター の.logファイルを遠隔監視するためのシステム。
- **InfluxDB** と **Grafana** を用いてネットワーク越しにリアルタイムで可視化します。  
- このリポジトリには、すぐに利用できる Grafana ダッシュボード（JSON）が含まれています。  
 
![外部向け説明資料](https://github.com/user-attachments/assets/eb5fce0c-8dbf-4847-b3d2-5c2d21164ab5)  
**注意：このプログラムはINFICON社の公式なものではありません。**  
**Note: This program is not official INFICON.**  
本システムで使用する物性値について、正確性を保証するものではありません。利用により生じたいかなる結果についても、作者は責任を負いません。  
電子ビーム蒸着装置に取り付けられたSTM-2を想定して作成。  

## ✨ 特長

- STM-2 の膜厚・成膜レート・周波数をリアルタイム監視
- ネットワーク経由での多地点同時監視
- 目標膜厚の 80% を超えるとパネルが赤く点灯してお知らせ
  
![alert](https://github.com/user-attachments/assets/a3f198d1-49f4-4ad0-a9d4-1652ef7358b8)


## STM-2接続パソコンの準備：
Windowsマシンを想定しています。  
Windows Defender ファイアウォールに受信規則を追加してポート3000を開放する。  
固定IPアドレスを設定する。あらかじめネットワーク管理者に確認することをおすすめします。 

### Pythonをインストール  
公式サイト： <a href="https://www.python.org/" target="blank">https://www.python.org/</a>  

コマンドプロンプトで下記の三つのコマンドを実行して必要なライブラリをインストールする。  

pip install influxdb  
pip install customtkinter  
pip install tkinterdnd2  

### InfluxDBをインストール  
公式サイト： <a href="https://www.influxdata.com/" target="blank">https://www.influxdata.com/</a>     
STM-2 のログスクリプトとの互換性のため、InfluxDB v1.x を推奨します。  

### Grafanaをインストール  
公式サイト： <a href="https://grafana.com/" target="_blank"> https://grafana.com/ </a>

"STM-2_dashboard.json" をインポートして各種設定を完了させる。  
- Grafana → Dashboards → Import  
- JSON Upload または JSON を貼り付け  
- Data source を InfluxDB に設定  

---
## 動作手順：
## 🖥️ **STM‑2 接続パソコンで行う作業**

### 1. **STM‑2専用ソフトウェア（INFICON）**
- INFICON公式 STM‑2 ソフトを起動  
- 必要な設定を行い、**記録 Start**

### 2. **InfluxDB の起動**
- InfluxDB のフォルダへ移動  
- Shift＋右クリック → **「ここでコマンドウィンドウを開く」**  
- コマンドプロンプトで  
  ```
  .\influxd
  ```  
  を実行し、InfluxDB を起動

### 3. **Python GUI（蒸着モニタリングアプリ）**
- Python コードを実行して GUI を起動
- 目標厚さ（nm）を入力  
- 蒸着材料を選択 → **密度・Z‑ratio が自動入力**  
- 「参照」ボタンから **STM‑2 のログファイル（現在記録中のもの）** を選択  
- GUI が InfluxDB にデータを書き込み始める

---

## 💻 **クライアントPC（遠隔監視側）で行う作業**

### 1. **Grafana へアクセス**
- Webブラウザを開く  
- STM‑2接続PCの固定IPアドレスを指定してアクセス  
  ```
  http://（STM‑2接続PCの固定IP）:3000
  ```
- Grafana ダッシュボードでリアルタイム監視

---

## 謝辞
- 本開発は文部科学省先端研究基盤共用促進事業（先端研究設備プラットフォームプログラム） JPMXS0450300021である パワーレーザーDXプラットフォーム で共用された機器を利用した成果です。
