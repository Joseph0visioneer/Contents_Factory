#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Shorts 데이터 수집기 - 초보자용
사용법: 이 파일을 실행하고 안내에 따라 진행하세요.
"""

import re
import pandas as pd
from datetime import datetime
import json

try:
    from googleapiclient.discovery import build
    print("✅ Google API 라이브러리 로드 성공")
except ImportError:
    print("❌ Google API 라이브러리가 설치되지 않았습니다.")
    print("다음 명령어를 실행하세요: pip install google-api-python-client")
    input("계속하려면 Enter를 누르세요...")
    exit()

class YouTubeShortsCollector:
    def __init__(self):
        self.api_key = None
        self.youtube = None
        self.results = []
    
    def setup_api_key(self):
        """API 키 설정"""
        print("\n" + "="*60)
        print("🔑 YouTube Data API 키 설정")
        print("="*60)
        
        while True:
            api_key = input("\n📋 API 키를 입력하세요: ").strip()
            
            if not api_key:
                print("❌ API 키를 입력해주세요.")
                continue
            
            if not api_key.startswith('AIza'):
                print("❌ 올바르지 않은 API 키 형식입니다.")
                print("💡 API 키는 'AIza'로 시작해야 합니다.")
                continue
            
            try:
                # API 키 테스트
                youtube = build('youtube', 'v3', developerKey=api_key)
                # 간단한 테스트 요청
                test_response = youtube.videos().list(
                    part='snippet',
                    id='dQw4w9WgXcQ'  # 테스트용 비디오 ID
                ).execute()
                
                self.api_key = api_key
                self.youtube = youtube
                print("✅ API 키가 정상적으로 설정되었습니다!")
                break
                
            except Exception as e:
                print(f"❌ API 키 오류: {e}")
                print("💡 API 키를 다시 확인해주세요.")
                continue
    
    def extract_video_id(self, url):
        """YouTube URL에서 비디오 ID 추출"""
        patterns = [
            r'(?:youtube\.com/shorts/)([^&\n?#]+)',
            r'(?:youtube\.com/watch\?v=)([^&\n?#]+)',
            r'(?:youtu\.be/)([^&\n?#]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def get_video_info(self, video_id):
        """비디오 정보 수집"""
        try:
            # 비디오 기본 정보
            video_response = self.youtube.videos().list(
                part='snippet,statistics,contentDetails',
                id=video_id
            ).execute()
            
            if not video_response['items']:
                return None
            
            video = video_response['items'][0]
            snippet = video['snippet']
            statistics = video['statistics']
            
            # 댓글 수집
            comments = self.get_comments(video_id)
            
            # 채널 정보
            channel_info = self.get_channel_info(snippet['channelId'])
            
            return {
                'video_id': video_id,
                'title': snippet.get('title', ''),
                'description': snippet.get('description', '')[:500] + '...' if len(snippet.get('description', '')) > 500 else snippet.get('description', ''),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'duration': video['contentDetails'].get('duration', ''),
                'tags': ', '.join(snippet.get('tags', [])),
                'category_id': snippet.get('categoryId', ''),
                'subscriber_count': channel_info.get('subscriber_count', 0) if channel_info else 0,
                'comments': comments
            }
            
        except Exception as e:
            print(f"❌ 비디오 정보 수집 오류: {e}")
            return None
    
    def get_comments(self, video_id, max_comments=20):
        """댓글 수집"""
        comments = []
        try:
            response = self.youtube.commentThreads().list(
                part='snippet',
                videoId=video_id,
                maxResults=max_comments,
                order='relevance'
            ).execute()
            
            for item in response['items']:
                comment = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'author': comment['authorDisplayName'],
                    'text': comment['textDisplay'],
                    'like_count': comment['likeCount'],
                    'published_at': comment['publishedAt']
                })
            
        except Exception as e:
            print(f"⚠️ 댓글 수집 중 오류 (건너뜀): {e}")
        
        return comments
    
    def get_channel_info(self, channel_id):
        """채널 정보 수집"""
        try:
            response = self.youtube.channels().list(
                part='statistics',
                id=channel_id
            ).execute()
            
            if response['items']:
                stats = response['items'][0]['statistics']
                return {
                    'subscriber_count': int(stats.get('subscriberCount', 0))
                }
        except:
            pass
        return None
    
    def collect_data(self):
        """데이터 수집 메인 함수"""
        print("\n" + "="*60)
        print("📊 YouTube Shorts 데이터 수집 시작")
        print("="*60)
        print("💡 팁: 'q' 입력 시 수집을 종료하고 결과를 저장합니다.")
        
        while True:
            print(f"\n현재 수집된 영상: {len(self.results)}개")
            url = input("\n🔗 YouTube Shorts URL을 입력하세요 (종료: q): ").strip()
            
            if url.lower() == 'q':
                break
            
            if not url:
                print("❌ URL을 입력해주세요.")
                continue
            
            video_id = self.extract_video_id(url)
            if not video_id:
                print("❌ 올바르지 않은 YouTube URL입니다.")
                continue
            
            print(f"🔍 영상 정보 수집 중... (ID: {video_id})")
            
            video_info = self.get_video_info(video_id)
            if video_info:
                self.results.append(video_info)
                print(f"✅ 수집 완료: {video_info['title'][:50]}...")
                print(f"   📊 조회수: {video_info['view_count']:,}")
                print(f"   👍 좋아요: {video_info['like_count']:,}")
                print(f"   💬 댓글: {video_info['comment_count']:,}")
            else:
                print("❌ 영상 정보를 가져올 수 없습니다.")
    
    def save_results(self):
        """결과 저장"""
        if not self.results:
            print("\n❌ 저장할 데이터가 없습니다.")
            return
        
        print(f"\n💾 {len(self.results)}개 영상 데이터 저장 중...")
        
        # Excel 파일로 저장
        try:
            # 기본 정보 데이터프레임
            basic_data = []
            for item in self.results:
                basic_data.append({
                    '영상 ID': item['video_id'],
                    '제목': item['title'],
                    '채널명': item['channel_title'],
                    '업로드 날짜': item['published_at'],
                    '조회수': item['view_count'],
                    '좋아요 수': item['like_count'],
                    '댓글 수': item['comment_count'],
                    '구독자 수': item['subscriber_count'],
                    '태그': item['tags'],
                    '설명': item['description']
                })
            
            # 댓글 데이터프레임
            comment_data = []
            for item in self.results:
                for comment in item['comments']:
                    comment_data.append({
                        '영상 ID': item['video_id'],
                        '영상 제목': item['title'],
                        '댓글 작성자': comment['author'],
                        '댓글 내용': comment['text'],
                        '댓글 좋아요': comment['like_count'],
                        '댓글 작성일': comment['published_at']
                    })
            
            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"YouTube_Shorts_Data_{timestamp}.xlsx"
            
            # Excel 파일 저장
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                pd.DataFrame(basic_data).to_excel(writer, sheet_name='영상정보', index=False)
                if comment_data:
                    pd.DataFrame(comment_data).to_excel(writer, sheet_name='댓글정보', index=False)
            
            print(f"✅ Excel 파일 저장 완료: {filename}")
            
            # JSON 파일도 저장 (백업용)
            json_filename = f"YouTube_Shorts_Data_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)
            
            print(f"✅ JSON 파일 저장 완료: {json_filename}")
            
        except Exception as e:
            print(f"❌ 파일 저장 오류: {e}")

def main():
    """메인 함수"""
    print("🎬 YouTube Shorts 데이터 수집기")
    print("=" * 60)
    print("📝 이 프로그램으로 할 수 있는 것:")
    print("   • YouTube Shorts 영상 정보 수집")
    print("   • 제목, 조회수, 좋아요, 댓글 등 상세 정보")
    print("   • Excel 파일로 자동 저장")
    print("=" * 60)
    
    collector = YouTubeShortsCollector()
    
    # API 키 설정
    collector.setup_api_key()
    
    # 데이터 수집
    collector.collect_data()
    
    # 결과 저장
    collector.save_results()
    
    print("\n🎉 프로그램 실행 완료!")
    print("📁 생성된 파일을 확인해보세요.")
    input("\n종료하려면 Enter를 누르세요...")

if __name__ == "__main__":
    main()