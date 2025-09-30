#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
YouTube Shorts 데이터 수집기 v2 - 배치 처리 버전
사용법: 이 파일을 실행하고 안내에 따라 진행하세요.

새로운 기능:
- CSV 파일에서 URL 배치 처리
- 키워드 태깅
- 썸네일 자동 다운로드
- 자막 추출 (있는 경우)
- 진행 상황 저장/재개
- Rate Limiting
- 중복 제거
"""

import re
import pandas as pd
from datetime import datetime
import json
import os
import time
import logging
from pathlib import Path
import requests

try:
    from googleapiclient.discovery import build
    print("✅ Google API 라이브러리 로드 성공")
except ImportError:
    print("❌ Google API 라이브러리가 설치되지 않았습니다.")
    print("다음 명령어를 실행하세요: pip install google-api-python-client")
    input("계속하려면 Enter를 누르세요...")
    exit()

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    print("✅ YouTube Transcript API 라이브러리 로드 성공")
except ImportError:
    print("❌ YouTube Transcript API 라이브러리가 설치되지 않았습니다.")
    print("다음 명령어를 실행하세요: pip install youtube-transcript-api")
    input("계속하려면 Enter를 누르세요...")
    exit()


class YouTubeShortsCollectorV2:
    def __init__(self):
        self.api_key = None
        self.youtube = None
        self.results = []
        self.processed_ids = set()
        self.failed_urls = []
        self.progress_file = "progress.json"
        self.api_key_file = "api_key.txt"
        self.thumbnail_dir = "thumbnails"
        self.setup_logging()
        self.api_call_delay = 0.5  # Rate limiting: 0.5초 대기

    def setup_logging(self):
        """로깅 설정"""
        logging.basicConfig(
            filename='youtube_collector.log',
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            encoding='utf-8'
        )
        self.logger = logging.getLogger(__name__)

    def load_api_key(self):
        """저장된 API 키 불러오기"""
        if os.path.exists(self.api_key_file):
            try:
                with open(self.api_key_file, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                self.logger.error(f"API 키 불러오기 실패: {e}")
        return None

    def save_api_key(self, api_key):
        """API 키 저장"""
        try:
            with open(self.api_key_file, 'w', encoding='utf-8') as f:
                f.write(api_key)
            self.logger.info("API 키 저장 완료")
        except Exception as e:
            self.logger.error(f"API 키 저장 실패: {e}")

    def setup_api_key(self):
        """API 키 설정"""
        print("\n" + "="*60)
        print("🔑 YouTube Data API 키 설정")
        print("="*60)

        # 저장된 API 키 확인
        saved_key = self.load_api_key()
        if saved_key:
            print(f"\n💾 저장된 API 키를 발견했습니다: {saved_key[:10]}...")
            use_saved = input("저장된 키를 사용하시겠습니까? (y/n): ").strip().lower()

            if use_saved == 'y':
                try:
                    # API 키 테스트
                    youtube = build('youtube', 'v3', developerKey=saved_key)
                    test_response = youtube.videos().list(
                        part='snippet',
                        id='dQw4w9WgXcQ'
                    ).execute()

                    self.api_key = saved_key
                    self.youtube = youtube
                    print("✅ 저장된 API 키로 설정 완료!")
                    self.logger.info("저장된 API 키 사용")
                    return
                except Exception as e:
                    print(f"❌ 저장된 API 키 오류: {e}")
                    print("💡 새로운 API 키를 입력해주세요.")

        # 새 API 키 입력
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
                test_response = youtube.videos().list(
                    part='snippet',
                    id='dQw4w9WgXcQ'
                ).execute()

                self.api_key = api_key
                self.youtube = youtube

                # API 키 저장 여부 확인
                save_choice = input("\n💾 이 API 키를 저장하시겠습니까? (y/n): ").strip().lower()
                if save_choice == 'y':
                    self.save_api_key(api_key)
                    print("✅ API 키가 저장되었습니다!")
                else:
                    print("✅ API 키가 설정되었습니다! (저장하지 않음)")

                self.logger.info("API 키 설정 완료")
                break

            except Exception as e:
                print(f"❌ API 키 오류: {e}")
                print("💡 API 키를 다시 확인해주세요.")
                self.logger.error(f"API 키 오류: {e}")
                continue

    def load_progress(self):
        """진행 상황 불러오기"""
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.results = data.get('results', [])
                    self.processed_ids = set(data.get('processed_ids', []))
                    self.failed_urls = data.get('failed_urls', [])
                print(f"📂 이전 진행 상황을 불러왔습니다. (수집된 영상: {len(self.results)}개)")
                self.logger.info(f"진행 상황 불러오기 완료: {len(self.results)}개")
                return True
            except Exception as e:
                print(f"⚠️ 진행 상황 불러오기 실패: {e}")
                self.logger.error(f"진행 상황 불러오기 실패: {e}")
        return False

    def save_progress(self):
        """진행 상황 저장"""
        try:
            data = {
                'results': self.results,
                'processed_ids': list(self.processed_ids),
                'failed_urls': self.failed_urls,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            self.logger.info(f"진행 상황 저장 완료: {len(self.results)}개")
        except Exception as e:
            print(f"⚠️ 진행 상황 저장 실패: {e}")
            self.logger.error(f"진행 상황 저장 실패: {e}")

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

    def download_thumbnail(self, video_id, thumbnail_url):
        """썸네일 다운로드"""
        try:
            # 썸네일 디렉토리 생성
            Path(self.thumbnail_dir).mkdir(exist_ok=True)

            # 파일명 생성
            filename = f"{video_id}.jpg"
            filepath = os.path.join(self.thumbnail_dir, filename)

            # 이미 다운로드된 경우 건너뛰기
            if os.path.exists(filepath):
                return filename

            # 썸네일 다운로드
            response = requests.get(thumbnail_url, timeout=10)
            if response.status_code == 200:
                with open(filepath, 'wb') as f:
                    f.write(response.content)
                return filename
            else:
                self.logger.warning(f"썸네일 다운로드 실패: {video_id}")
                return None

        except Exception as e:
            self.logger.error(f"썸네일 다운로드 오류 ({video_id}): {e}")
            return None

    def get_transcript(self, video_id):
        """자막 추출"""
        try:
            # 한국어 자막 우선, 없으면 자동생성 자막, 그것도 없으면 영어
            transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

            try:
                # 한국어 자막 시도
                transcript = transcript_list.find_transcript(['ko'])
            except:
                try:
                    # 자동생성 한국어 자막 시도
                    transcript = transcript_list.find_generated_transcript(['ko'])
                except:
                    try:
                        # 영어 자막 시도
                        transcript = transcript_list.find_transcript(['en'])
                    except:
                        return None

            # 자막 텍스트 추출
            transcript_data = transcript.fetch()
            full_text = ' '.join([entry['text'] for entry in transcript_data])
            return full_text

        except Exception as e:
            self.logger.info(f"자막 없음 ({video_id}): {str(e)}")
            return None

    def get_video_info(self, video_id, keyword=None):
        """비디오 정보 수집"""
        try:
            # Rate Limiting
            time.sleep(self.api_call_delay)

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

            # 썸네일 URL 및 다운로드
            thumbnails = snippet.get('thumbnails', {})
            thumbnail_url = thumbnails.get('medium', {}).get('url', '')
            thumbnail_filename = self.download_thumbnail(video_id, thumbnail_url) if thumbnail_url else None

            # 자막 추출
            transcript = self.get_transcript(video_id)

            # Rate Limiting
            time.sleep(self.api_call_delay)

            # 댓글 수집
            comments = self.get_comments(video_id)

            # Rate Limiting
            time.sleep(self.api_call_delay)

            # 채널 정보
            channel_info = self.get_channel_info(snippet['channelId'])

            return {
                'video_id': video_id,
                'keyword': keyword or '',
                'title': snippet.get('title', ''),
                'description': snippet.get('description', ''),
                'channel_title': snippet.get('channelTitle', ''),
                'published_at': snippet.get('publishedAt', ''),
                'view_count': int(statistics.get('viewCount', 0)),
                'like_count': int(statistics.get('likeCount', 0)),
                'comment_count': int(statistics.get('commentCount', 0)),
                'duration': video['contentDetails'].get('duration', ''),
                'tags': ', '.join(snippet.get('tags', [])),
                'category_id': snippet.get('categoryId', ''),
                'subscriber_count': channel_info.get('subscriber_count', 0) if channel_info else 0,
                'thumbnail_filename': thumbnail_filename or '',
                'transcript': transcript or '',
                'comments': comments
            }

        except Exception as e:
            self.logger.error(f"비디오 정보 수집 오류 ({video_id}): {e}")
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
            self.logger.info(f"댓글 수집 불가 ({video_id}): {str(e)}")

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
        except Exception as e:
            self.logger.error(f"채널 정보 수집 오류 ({channel_id}): {e}")
        return None

    def load_urls_from_csv(self, csv_source):
        """CSV 파일 또는 URL에서 URL 목록 읽기"""
        try:
            # URL인지 파일 경로인지 확인
            if csv_source.startswith('http://') or csv_source.startswith('https://'):
                print(f"\n🌐 웹에서 CSV 다운로드 중...")
                df = pd.read_csv(csv_source, encoding='utf-8')
            else:
                print(f"\n📂 로컬 CSV 파일 읽는 중...")
                df = pd.read_csv(csv_source, encoding='utf-8')

            # CSV 구조 분석
            print(f"\n📊 CSV 데이터 분석:")
            print(f"   총 행 수: {len(df)}")
            print(f"   컬럼: {list(df.columns)}")

            # URL 추출 로직
            urls_with_keywords = []

            # 첫 번째 컬럼이 키워드라고 가정
            keyword_col = df.columns[0]

            for idx, row in df.iterrows():
                keyword = row[keyword_col]
                # 각 행의 모든 셀을 검사하여 YouTube URL 찾기
                for col in df.columns[1:]:
                    cell_value = str(row[col])
                    if 'youtube.com' in cell_value or 'youtu.be' in cell_value:
                        urls_with_keywords.append({
                            'url': cell_value.strip(),
                            'keyword': keyword
                        })

            print(f"   추출된 URL: {len(urls_with_keywords)}개")
            return urls_with_keywords

        except Exception as e:
            print(f"❌ CSV 읽기 오류: {e}")
            self.logger.error(f"CSV 읽기 오류: {e}")
            return []

    def collect_from_csv(self, csv_path):
        """CSV 파일에서 URL 목록을 읽어 배치 처리"""
        print("\n" + "="*60)
        print("📊 CSV 파일에서 URL 배치 수집 시작")
        print("="*60)

        # CSV 파일 읽기
        urls_data = self.load_urls_from_csv(csv_path)

        if not urls_data:
            print("❌ 처리할 URL이 없습니다.")
            return

        total = len(urls_data)
        print(f"\n📋 총 {total}개의 URL을 처리합니다.")

        # 진행 상황 표시
        for idx, data in enumerate(urls_data, 1):
            url = data['url']
            keyword = data['keyword']

            print(f"\n{'='*60}")
            print(f"진행: {idx}/{total} ({idx/total*100:.1f}%)")
            print(f"키워드: {keyword}")
            print(f"URL: {url[:80]}...")

            video_id = self.extract_video_id(url)

            if not video_id:
                print("❌ 올바르지 않은 YouTube URL")
                self.failed_urls.append({'url': url, 'keyword': keyword, 'reason': 'Invalid URL'})
                self.logger.warning(f"잘못된 URL: {url}")
                continue

            # 중복 체크
            if video_id in self.processed_ids:
                print(f"⏭️  이미 수집된 영상 (ID: {video_id})")
                continue

            print(f"🔍 영상 정보 수집 중... (ID: {video_id})")

            video_info = self.get_video_info(video_id, keyword)

            if video_info:
                self.results.append(video_info)
                self.processed_ids.add(video_id)

                print(f"✅ 수집 완료: {video_info['title'][:50]}...")
                print(f"   📊 조회수: {video_info['view_count']:,}")
                print(f"   👍 좋아요: {video_info['like_count']:,}")
                print(f"   💬 댓글: {video_info['comment_count']:,}")
                print(f"   📝 자막: {'있음' if video_info['transcript'] else '없음'}")
                print(f"   🖼️  썸네일: {'저장됨' if video_info['thumbnail_filename'] else '실패'}")

                self.logger.info(f"수집 완료: {video_id} - {video_info['title']}")
            else:
                print("❌ 영상 정보를 가져올 수 없습니다.")
                self.failed_urls.append({'url': url, 'keyword': keyword, 'reason': 'Failed to fetch'})
                self.logger.error(f"수집 실패: {url}")

            # 10개마다 중간 저장
            if idx % 10 == 0:
                print("\n💾 중간 저장 중...")
                self.save_progress()

        # 최종 저장
        print("\n💾 최종 진행 상황 저장 중...")
        self.save_progress()

        # 통계 출력
        self.print_statistics()

    def print_statistics(self):
        """수집 통계 출력"""
        print("\n" + "="*60)
        print("📈 수집 통계")
        print("="*60)
        print(f"✅ 성공: {len(self.results)}개")
        print(f"❌ 실패: {len(self.failed_urls)}개")

        if self.results:
            # 키워드별 통계
            keywords = {}
            for item in self.results:
                kw = item.get('keyword', '미분류')
                if kw not in keywords:
                    keywords[kw] = {'count': 0, 'total_views': 0}
                keywords[kw]['count'] += 1
                keywords[kw]['total_views'] += item['view_count']

            print(f"\n📊 키워드별 통계:")
            for kw, stats in keywords.items():
                avg_views = stats['total_views'] / stats['count']
                print(f"   {kw}: {stats['count']}개 (평균 조회수: {avg_views:,.0f})")

        if self.failed_urls:
            print(f"\n❌ 실패한 URL:")
            for item in self.failed_urls[:5]:  # 최대 5개만 표시
                print(f"   {item['url'][:60]}... - {item['reason']}")
            if len(self.failed_urls) > 5:
                print(f"   ... 외 {len(self.failed_urls) - 5}개")

    def save_results(self):
        """결과 저장"""
        if not self.results:
            print("\n❌ 저장할 데이터가 없습니다.")
            return

        print(f"\n💾 {len(self.results)}개 영상 데이터 저장 중...")

        try:
            # 기본 정보 데이터프레임
            basic_data = []
            for item in self.results:
                basic_data.append({
                    '영상 ID': item['video_id'],
                    '키워드': item.get('keyword', ''),
                    '제목': item['title'],
                    '채널명': item['channel_title'],
                    '업로드 날짜': item['published_at'],
                    '조회수': item['view_count'],
                    '좋아요 수': item['like_count'],
                    '댓글 수': item['comment_count'],
                    '구독자 수': item['subscriber_count'],
                    '태그': item['tags'],
                    '설명': item['description'],
                    '썸네일 파일명': item.get('thumbnail_filename', '')
                })

            # 댓글 데이터프레임
            comment_data = []
            for item in self.results:
                for comment in item['comments']:
                    comment_data.append({
                        '영상 ID': item['video_id'],
                        '키워드': item.get('keyword', ''),
                        '영상 제목': item['title'],
                        '댓글 작성자': comment['author'],
                        '댓글 내용': comment['text'],
                        '댓글 좋아요': comment['like_count'],
                        '댓글 작성일': comment['published_at']
                    })

            # 스크립트 데이터프레임
            script_data = []
            for item in self.results:
                if item.get('transcript'):
                    script_data.append({
                        '영상 ID': item['video_id'],
                        '키워드': item.get('keyword', ''),
                        '영상 제목': item['title'],
                        '스크립트': item['transcript']
                    })

            # 파일명 생성
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"YouTube_Shorts_Data_{timestamp}.xlsx"

            # Excel 파일 저장
            with pd.ExcelWriter(filename, engine='openpyxl') as writer:
                pd.DataFrame(basic_data).to_excel(writer, sheet_name='영상정보', index=False)
                if comment_data:
                    pd.DataFrame(comment_data).to_excel(writer, sheet_name='댓글정보', index=False)
                if script_data:
                    pd.DataFrame(script_data).to_excel(writer, sheet_name='스크립트', index=False)

            print(f"✅ Excel 파일 저장 완료: {filename}")

            # JSON 파일도 저장 (백업용)
            json_filename = f"YouTube_Shorts_Data_{timestamp}.json"
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(self.results, f, ensure_ascii=False, indent=2)

            print(f"✅ JSON 파일 저장 완료: {json_filename}")

            # 실패 목록 저장
            if self.failed_urls:
                failed_filename = f"Failed_URLs_{timestamp}.json"
                with open(failed_filename, 'w', encoding='utf-8') as f:
                    json.dump(self.failed_urls, f, ensure_ascii=False, indent=2)
                print(f"⚠️  실패 URL 목록 저장: {failed_filename}")

            self.logger.info(f"결과 저장 완료: {filename}")

        except Exception as e:
            print(f"❌ 파일 저장 오류: {e}")
            self.logger.error(f"파일 저장 오류: {e}")


def main():
    """메인 함수"""
    print("🎬 YouTube Shorts 데이터 수집기 v2")
    print("=" * 60)
    print("📝 새로운 기능:")
    print("   • CSV 파일에서 URL 배치 처리")
    print("   • 키워드 태깅")
    print("   • 썸네일 자동 다운로드")
    print("   • 자막 추출 (있는 경우)")
    print("   • 진행 상황 자동 저장")
    print("   • Excel 파일로 자동 저장")
    print("=" * 60)

    collector = YouTubeShortsCollectorV2()

    # 이전 진행 상황 불러오기 선택
    if os.path.exists(collector.progress_file):
        choice = input("\n이전 진행 상황을 불러오시겠습니까? (y/n): ").strip().lower()
        if choice == 'y':
            collector.load_progress()

    # API 키 설정
    collector.setup_api_key()

    # CSV 파일 경로 또는 URL 입력
    print("\n" + "="*60)
    print("📁 CSV 데이터 소스 선택")
    print("="*60)
    print("💡 CSV 입력 방법:")
    print("   1. 로컬 파일 경로 (예: ./data.csv)")
    print("   2. 구글 시트 웹 발행 URL (CSV 형식)")
    print("\n💡 CSV 파일 형식:")
    print("   - 첫 번째 컬럼: 키워드")
    print("   - 나머지 컬럼: YouTube URL")
    print("\n💡 구글 시트 웹 발행 방법:")
    print("   파일 > 공유 > 웹에 게시 > '쉼표로 구분된 값(.csv)' 선택")

    while True:
        csv_source = input("\n📋 CSV 파일 경로 또는 URL을 입력하세요: ").strip()

        if not csv_source:
            print("❌ 입력이 비어있습니다. 다시 입력해주세요.")
            continue

        # URL이거나 파일이 존재하면 진행
        if csv_source.startswith('http://') or csv_source.startswith('https://'):
            print("✅ 웹 URL로 인식되었습니다.")
            break
        elif os.path.exists(csv_source):
            print("✅ 로컬 파일로 인식되었습니다.")
            break
        else:
            print("❌ 파일을 찾을 수 없습니다. URL이거나 올바른 파일 경로를 입력해주세요.")

    # 데이터 수집
    collector.collect_from_csv(csv_source)

    # 결과 저장
    collector.save_results()

    print("\n🎉 프로그램 실행 완료!")
    print("📁 생성된 파일을 확인해보세요.")
    print(f"   - Excel 파일")
    print(f"   - JSON 파일")
    print(f"   - 썸네일: {collector.thumbnail_dir}/ 폴더")
    print(f"   - 로그: youtube_collector.log")
    input("\n종료하려면 Enter를 누르세요...")


if __name__ == "__main__":
    main()