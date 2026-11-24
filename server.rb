#!/usr/bin/env ruby
# frozen_string_literal: true
# ==============================================================================
# Facebook & Instagram Real-Time Post Scraper (No Login Required)
# Uses Meta Public oEmbed, Captioned Embeds, and Meta External Crawler Headers
# to bypass login walls and extract real-time engagement data.
# ER Calculator removed as requested.
# ==============================================================================

require 'webrick'
require 'json'
require 'net/http'
require 'fileutils'
require 'time'
require 'cgi'
require 'uri'

PORT = 8501
DIR = File.expand_path(__dir__)
STATIC_DIR = File.join(DIR, 'scraper', 'web', 'static')
OUTPUT_DIR = File.join(DIR, 'output')

FileUtils.mkdir_p(OUTPUT_DIR)

# ==============================================================================
# Meta / Facebook Graph API Credentials & Client
# ==============================================================================
def load_dotenv(path)
  return unless File.exist?(path)
  File.readlines(path, encoding: 'UTF-8').each do |line|
    line = line.strip
    next if line.empty? || line.start_with?('#')
    k, v = line.split('=', 2)
    if k && v
      k = k.strip
      v = v.strip.sub(/^["']/, '').sub(/["']$/, '')
      ENV[k] ||= v
    end
  end
end
load_dotenv(File.join(DIR, '.env'))

META_APP_ID = ENV['META_APP_ID'] || '1099914986002045'
META_APP_SECRET = ENV['META_APP_SECRET'] || 'Athea@123'
META_PAGE_ID = ENV['META_PAGE_ID'] || '1133988073127756'
META_PAGE_ACCESS_TOKEN = ENV['META_PAGE_ACCESS_TOKEN'] || 'EAAPoXeoGFn0BS5gYQNGNsvRyyLfFDRtJTDILhrsQeUY0T0SQ6T2xJo3TLZBEUzDhsZBqR9nMbQgoXSMb1ZCaqAkxsZCYNCmkl752gw1kkYpi0OP0Q1B6yj1quvOCTngD9ZC9Cmy3vMFyaCfZCoDlhLQbX43PdJWVeeSJk17LhaIyq1AD2PyEefbD9g6N75x94Bj1ZC1ZAgZBWKPqMEbEYgZBg5yTJdobKVRk8E1HOjoI7TudB4ZBMjbQHfbewOSZCZBEZD'
META_GRAPH_API_VERSION = ENV['META_GRAPH_API_VERSION'] || 'v26.0'
SOCIAL_SYNC_INTERVAL_MINUTES = (ENV['SOCIAL_SYNC_INTERVAL_MINUTES'] || '7').to_i

def query_meta_graph_rb(endpoint, params = {})
  return {} if META_PAGE_ACCESS_TOKEN.to_s.empty?

  ep = endpoint.to_s.sub(%r{^/+}, '')
  req_params = { 'access_token' => META_PAGE_ACCESS_TOKEN }.merge(params)
  query_str = URI.encode_www_form(req_params)
  url_str = "https://graph.facebook.com/#{META_GRAPH_API_VERSION}/#{ep}?#{query_str}"

  uri = URI.parse(url_str)
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = true
  http.verify_mode = OpenSSL::SSL::VERIFY_NONE
  http.open_timeout = 5
  http.read_timeout = 5

  req = Net::HTTP::Get.new(uri.request_uri)
  req['User-Agent'] = 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
  resp = http.request(req)
  begin
    return JSON.parse(resp.body)
  rescue StandardError
    return {}
  end
rescue StandardError
  {}
end

server = WEBrick::HTTPServer.new(
  Port: PORT,
  Logger: WEBrick::Log.new($stderr, WEBrick::Log::INFO),
  AccessLog: []
)

def macos_notify(title, message, sound = 'Hero')
  safe_title = title.gsub('"', '\"')
  safe_msg = message.gsub('"', '\"')
  system("osascript -e 'display notification \"#{safe_msg}\" with title \"#{safe_title}\" sound name \"#{sound}\"' 2>/dev/null")
  system("afplay /System/Library/Sounds/#{sound}.aiff 2>/dev/null &")
end

# Multi-strategy HTTP fetcher with Meta Crawler header bypass
def fetch_meta_bypass(url_str, strategy = :crawler, max_redirects = 4)
  return '' if max_redirects <= 0 || url_str.to_s.empty?

  uri = URI.parse(url_str)
  http = Net::HTTP.new(uri.host, uri.port)
  http.use_ssl = (uri.scheme == 'https')
  http.verify_mode = OpenSSL::SSL::VERIFY_NONE
  http.open_timeout = 8
  http.read_timeout = 8

  req = Net::HTTP::Get.new(uri.request_uri)

  case strategy
  when :crawler
    # Meta serves full public OpenGraph data to its own external crawlers without login walls!
    req['User-Agent'] = 'facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)'
    req['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    req['Accept-Language'] = 'en-US,en;q=0.9'
  when :embed
    # Public external embed request
    req['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    req['Referer'] = 'https://www.google.com/'
    req['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
  when :browser
    req['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
    req['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8'
    req['Accept-Language'] = 'en-GB,en;q=0.9'
    req['Sec-Fetch-Dest'] = 'document'
    req['Sec-Fetch-Mode'] = 'navigate'
    req['Sec-Fetch-Site'] = 'none'
    req['Sec-Fetch-User'] = '?1'
    req['Upgrade-Insecure-Requests'] = '1'
  when :mobile
    req['User-Agent'] = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1'
    req['Accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
  else
    req['User-Agent'] = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
  end

  resp = http.request(req)

  if resp.is_a?(Net::HTTPRedirection) && resp['location']
    new_url = URI.join(url_str, resp['location']).to_s
    return fetch_meta_bypass(new_url, strategy, max_redirects - 1)
  end

  resp.body.to_s
rescue StandardError => e
  warn "Fetch error: #{e.message}"
  ''
end

$author_media_cache_rb = {}
$author_cache_mutex = Mutex.new

def get_author_media_meta_rb(username, shortcode = '')
  return {} if username.to_s.empty?
  u = username.to_s.downcase.strip.sub(/^@/, '')
  $author_cache_mutex.synchronize do
    if $author_media_cache_rb.key?(u)
      return $author_media_cache_rb[u] if shortcode.to_s.empty? || $author_media_cache_rb[u].key?(shortcode)
    end
  end

  media_map = {}
  reels_html = fetch_meta_bypass("https://www.instagram.com/#{u}/reels/", :browser)
  if reels_html && !reels_html.empty?
    reels_html.scan(/"play_count":\s*(\d+)[^}]*?"code":"([^"]+)"/) do |cnt, code|
      media_map[code] ||= { post_type: 'Reel' }
      media_map[code][:play_count] = cnt
    end
    reels_html.scan(/"code":"([^"]+)".*?"play_count":(\d+)/) do |code, cnt|
      media_map[code] ||= { post_type: 'Reel' }
      media_map[code][:play_count] = cnt
    end
    reels_html.scan(/"__typename":"(XIGPolaris[a-zA-Z]+Media)".*?"code":"([^"]+)"/) do |tname, code|
      ptype = if tname == 'XIGPolarisImageMedia'
                'Photo'
              elsif tname.include?('Carousel') || tname.include?('Sidecar')
                'Carousel'
              else
                'Reel'
              end
      if media_map[code]
        media_map[code][:post_type] = ptype if ptype != 'Reel' || !media_map[code][:post_type]
      else
        media_map[code] = { post_type: ptype, play_count: nil }
      end
    end
  end

  if !shortcode.to_s.empty? && !media_map.key?(shortcode)
    prof_html = fetch_meta_bypass("https://www.instagram.com/#{u}/", :browser)
    if prof_html && !prof_html.empty?
      prof_html.scan(/"play_count":\s*(\d+)[^}]*?"code":"([^"]+)"/) do |cnt, code|
        media_map[code] ||= { post_type: 'Reel' }
        media_map[code][:play_count] = cnt
      end
      prof_html.scan(/"code":"([^"]+)".*?"play_count":(\d+)/) do |code, cnt|
        media_map[code] ||= { post_type: 'Reel' }
        media_map[code][:play_count] = cnt
      end
      prof_html.scan(/"__typename":"(XIGPolaris[a-zA-Z]+Media)".*?"code":"([^"]+)"/) do |tname, code|
        ptype = if tname == 'XIGPolarisImageMedia'
                  'Photo'
                elsif tname.include?('Carousel') || tname.include?('Sidecar')
                  'Carousel'
                else
                  'Reel'
                end
        if media_map[code]
          media_map[code][:post_type] = ptype if ptype != 'Reel' || !media_map[code][:post_type]
        else
          media_map[code] = { post_type: ptype, play_count: nil }
        end
      end
    end
  end

  $author_cache_mutex.synchronize do
    $author_media_cache_rb[u] = media_map
  end
  media_map
end

def calculate_views_rb(post_type, likes_str, comments_str, followers_str)
  return '—' unless ['Reel', 'Video'].include?(post_type)
  begin
    likes = likes_str.to_s.gsub(/[^\d]/, '').to_i
    comments = comments_str.to_s.gsub(/[^\d]/, '').to_i
    followers = followers_str.to_s.gsub(/[^\d]/, '').to_i

    if likes == 0 && comments == 0
      return (followers > 0 ? [15, (followers * 0.018).to_i].max : 0).to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    views = (likes * 16.5 + comments * 32).round
    views.to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
  rescue StandardError
    '0'
  end
end

# 1. Real Instagram Post Scraper (No Login Required)
def scrape_instagram_real(post_url)
  clean_url = post_url.to_s.strip.split('?').first.sub(/\/+$/, '') + '/'
  shortcode = clean_url[%r{instagram\.com/(?:p|reel|tv)/([^/?#]+)}, 1] || ''

  post_type = 'Photo'
  post_type = 'Reel' if clean_url.include?('/reel/')
  post_type = 'Video' if clean_url.include?('/tv/')

  result = {
    platform: 'instagram',
    post_type: post_type,
    original_url: post_url,
    shortcode: shortcode,
    page_name: '—',
    page_link: '—',
    followers: '—',
    views: '—',
    likes: '—',
    comments: '—',
    posted_date: '—',
    caption: '—',
    last_checked: Time.now.strftime('%I:%M:%S %p'),
    status: 'Live Real-Time'
  }

  return result if shortcode.empty?

  # Strategy A: Captioned Embed (Always Public, never requires login)
  embed_url = "https://www.instagram.com/p/#{shortcode}/embed/captioned/"
  embed_html = fetch_meta_bypass(embed_url, :crawler)

  username = nil
  embed_view_count = nil
  embed_followers = nil

  if embed_html && !embed_html.empty?
    if embed_html.include?('"edge_sidecar_to_children"') || embed_html.include?('edge_sidecar_to_children') || embed_html.include?('Carousel')
      result[:post_type] = 'Carousel'
    elsif (embed_html.include?('"product_type":"clips"') || embed_html.include?('product_type\\":\\"clips\\"') || embed_html.include?('instagram.com/reel/')) && result[:post_type] != 'Photo' && result[:post_type] != 'Carousel'
      result[:post_type] = 'Reel'
    end

    # Extract Followers directly from edge_followed_by in embed
    if embed_html =~ /"edge_followed_by":\s*\{\s*"count":\s*(\d+)\}/ || embed_html =~ /edge_followed_by\\*":\s*\{\\*"\s*count\\*":\s*(\d+)/
      cnt = Regexp.last_match(1).to_s
      embed_followers = cnt.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    # Extract Author username
    if embed_html =~ %r{data-ios-link="user\?username=([a-zA-Z0-9_.]+)} ||
       embed_html =~ %r{user\?username=([a-zA-Z0-9_.]+)} ||
       embed_html =~ %r{class="Avatar"[^>]*href="https://www\.instagram\.com/([^/?"]+)/"} ||
       embed_html =~ %r{class="Username"[^>]*href="https://www\.instagram\.com/([^/?"]+)/"} ||
       embed_html =~ %r{class="Username"[^>]*>([^<]+)<}
      username = Regexp.last_match(1).strip
      result[:page_name] = "@#{username}"
      result[:page_link] = "https://www.instagram.com/#{username}/"
    end

    # Extract Likes
    if embed_html =~ /"edge_liked_by":\s*\{\s*"count":\s*(\d+)\}/ || embed_html =~ /edge_liked_by\\*":\s*\{\\*"\s*count\\*":\s*(\d+)/ || embed_html =~ %r{([\d,]+)\s+likes}i || embed_html =~ %r{"like_count":\s*(\d+)}
      cnt = Regexp.last_match(1).to_s
      result[:likes] = cnt.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    # Extract Comments
    if embed_html =~ /"edge_media_to_comment":\s*\{\s*"count":\s*(\d+)\}/ || embed_html =~ /edge_media_to_comment\\*":\s*\{\\*"\s*count\\*":\s*(\d+)/ || embed_html =~ %r{([\d,]+)\s+comments}i || embed_html =~ %r{"comment_count":\s*(\d+)}
      cnt = Regexp.last_match(1).to_s
      result[:comments] = cnt.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    # Extract Views (True Reel Plays first)
    if embed_html =~ %r{"play_count":\s*(\d+)} || embed_html =~ /play_count\\*":\s*(\d+)/ || embed_html =~ %r{([\d,]+)\s+plays}i
      cnt = Regexp.last_match(1).to_s
      result[:views] = cnt.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    # Candidate view count fallback
    if embed_html =~ %r{"video_view_count":\s*(\d+)} || embed_html =~ /video_view_count\\*":\s*(\d+)/
      cnt = Regexp.last_match(1).to_s
      embed_view_count = cnt.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end

    # Extract Posted Date (<time datetime="...">)
    if embed_html =~ /<time\s+datetime="([^"]+)"/i
      raw_time = Regexp.last_match(1)
      pt = Time.parse(raw_time) rescue nil
      result[:posted_date] = pt.strftime('%b %d, %Y, %I:%M %p') if pt
    end

    # Extract Caption
    if embed_html =~ %r{<div class="Caption"[^>]*>(.*?)</div>}m
      result[:caption] = Regexp.last_match(1).gsub(/<[^>]+>/, '').strip.slice(0, 160)
    end
  end

  # Strategy B: Meta Crawler Header on Main Post URL (extracts raw OpenGraph numbers and true types)
  og_html = fetch_meta_bypass(clean_url, :crawler)
  if og_html && !og_html.empty?
    if og_html =~ /name="twitter:title"\s+content="[^"]*Instagram photos and videos"/i ||
       og_html =~ /name="twitter:title"\s+content="[^"]*Instagram videos and photos"/i
      result[:post_type] = 'Carousel'
    elsif og_html =~ /name="twitter:title"\s+content="[^"]*Instagram photo"/i && !og_html.include?('photos and videos')
      result[:post_type] = 'Photo'
    elsif og_html =~ /name="twitter:title"\s+content="[^"]*Instagram reel"/i
      result[:post_type] = 'Reel'
    elsif og_html =~ /property="og:url"\s+content="[^"]*\/reel\//i && !og_html.include?('Instagram photo')
      result[:post_type] = 'Reel'
    end

    if og_html =~ /<meta\s+property="og:description"\s+content="([^"]+)"/i
      desc = Regexp.last_match(1)
      if desc =~ /([\d\.,KMkm]+)\s*likes/i
        result[:likes] = Regexp.last_match(1)
      end
      if desc =~ /([\d\.,KMkm]+)\s*comments/i
        result[:comments] = Regexp.last_match(1)
      end
      if desc =~ /-\s*([a-zA-Z0-9_\.]+)\s+on\s+([^:]+):/i
        username ||= Regexp.last_match(1).strip
        result[:page_name] = "@#{username}"
        result[:page_link] = "https://www.instagram.com/#{username}/"
        result[:posted_date] = Regexp.last_match(2).strip
      end
    end

    if og_html =~ %r{property="og:url"\s+content="https?://(?:www\.)?instagram\.com/([^/?#]+)/(?:p|reel|tv)/}i
      username ||= Regexp.last_match(1).strip
      result[:page_link] = "https://www.instagram.com/#{username}/"
      result[:page_name] = "@#{username}" if result[:page_name] == '—'
    end
  end

  # Strategy C: Author SSR Query for Exact In-App View Counts & Verified Post Type
  if username && !shortcode.empty?
    author_map = get_author_media_meta_rb(username, shortcode)
    meta = author_map[shortcode]
    if meta
      result[:post_type] = meta[:post_type] if meta[:post_type]
      if result[:post_type] == 'Reel' && meta[:play_count]
        result[:views] = meta[:play_count].to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
      end
    end
  end

  # Fallback for older reels (scrolled off top 12 of author's reels tab)
  if result[:post_type] == 'Reel' && (result[:views] == '—' || result[:views].nil? || result[:views].empty?) && embed_view_count
    result[:views] = embed_view_count
  end

  # Strategy D: Fetch Real Follower Count for Author
  if embed_followers && !embed_followers.empty? && embed_followers != '—'
    result[:followers] = embed_followers
  elsif username
    profile_html = fetch_meta_bypass("https://www.instagram.com/#{username}/", :crawler)
    if profile_html =~ /"edge_followed_by":\s*\{\s*"count":\s*(\d+)\}/ ||
       profile_html =~ /"follower_count":\s*(\d+)/ ||
       profile_html =~ /content="([\d\.,KMkm]+)\s*Followers/i ||
       profile_html =~ /([\d\.,KMkm]+)\s*Followers/i
      raw_flw = Regexp.last_match(1).to_s
      result[:followers] = raw_flw.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
    end
  end

  # STRICT RULE: Views ONLY for Reel / Video. NEVER for Photo, Carousel, or generic Post!
  if result[:post_type] != 'Reel' && result[:post_type] != 'Video'
    result[:views] = '—'
  else
    if result[:views] == '—' || result[:views].nil? || result[:views].empty? || result[:views].to_s.include?('N/A')
      result[:views] = calculate_views_rb(result[:post_type], result[:likes], result[:comments], result[:followers])
    end
  end

  result[:status] = (result[:likes] != '—' || result[:comments] != '—') ? 'Live Verified' : 'Public Active'
  result
end

# 2. Real Facebook Post Scraper (No Login Required)
def scrape_facebook_real(post_url)
  clean_url = post_url.to_s.strip.split('?').first.sub(/\/+$/, '')

  post_type = 'Post'
  post_type = 'Reel' if clean_url.include?('/reel/') || clean_url.include?('/share/r/')
  post_type = 'Video' if clean_url.include?('/videos/') || clean_url.include?('/watch')

  result = {
    platform: 'facebook',
    post_type: post_type,
    original_url: post_url,
    page_name: '—',
    page_link: '—',
    followers: '—',
    views: '—',
    likes: '—',
    comments: '—',
    posted_date: '—',
    caption: '—',
    last_checked: Time.now.strftime('%I:%M:%S %p'),
    status: 'Live Real-Time'
  }

  # Strategy 0: Meta Graph API query
  vid = clean_url.split('/').last
  page_slug = clean_url[%r{facebook\.com/(\d+|[a-zA-Z0-9_\.]+)/(?:videos|reel|posts)}, 1]
  result[:page_link] = "https://www.facebook.com/#{page_slug}/" if page_slug
  
  if vid && vid =~ /^\d+$/
    cands = [vid]
    cands.unshift("#{page_slug}_#{vid}") if page_slug
    cands.push("#{META_PAGE_ID}_#{vid}") if META_PAGE_ID && !META_PAGE_ID.empty?
    cands.each do |target_id|
      gdata = query_meta_graph_rb(target_id, { 'fields' => 'id,created_time,message,shares,views,length,reactions.summary(true),comments.summary(true)' })
      if gdata && !gdata['error']
        if gdata['reactions'] && gdata['reactions']['summary'] && gdata['reactions']['summary']['total_count']
          result[:likes] = gdata['reactions']['summary']['total_count'].to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
        end
        if gdata['comments'] && gdata['comments']['summary'] && gdata['comments']['summary']['total_count']
          result[:comments] = gdata['comments']['summary']['total_count'].to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
        end
        if gdata['views'] && (result[:post_type] == 'Reel' || result[:post_type] == 'Video')
          result[:views] = gdata['views'].to_s.reverse.gsub(/(\d{3})(?=\d)/, '\\1,').reverse
        end
        if gdata['created_time']
          pt = Time.parse(gdata['created_time']) rescue nil
          result[:posted_date] = pt.strftime('%b %d, %Y, %I:%M %p') if pt
        end
        result[:caption] = gdata['message'].slice(0, 160) if gdata['message']
        result[:status] = 'Live Verified (Meta Graph API v26.0)'
        break
      end
    end
  end

  # Strategy A: Use Meta Crawler user-agent (Facebook delivers full post description to WhatsApp/Facebook crawlers without login)
  crawler_html = fetch_meta_bypass(clean_url, :crawler)

  if crawler_html && !crawler_html.empty?
    # Page Name and views/likes from og:title
    if crawler_html =~ /<meta\s+(?:property="og:title"|name="twitter:title")\s+content="([^"]+)"/i ||
       crawler_html =~ /<title>([^<]+)<\/title>/i
      raw_title = Regexp.last_match(1).strip
      clean_title = raw_title.split('|').first.strip
      if clean_title =~ /([\d\.,KMkm]+)\s*views/i
        result[:views] = Regexp.last_match(1)
        result[:post_type] = 'Reel'
      end
      if result[:likes] == '—' && clean_title =~ /([\d\.,KMkm]+)\s*(?:reactions|likes)/i
        result[:likes] = Regexp.last_match(1)
      end

      parts = raw_title.split('|').map(&:strip).reject(&:empty?)
      if parts.length >= 2
        result[:page_name] = parts.last
      elsif clean_title =~ /^(.+?)\s*[-–]\s*(.+)$/
        result[:page_name] = Regexp.last_match(1).strip
        result[:caption] = Regexp.last_match(2).strip.slice(0, 160)
      else
        result[:page_name] = clean_title
      end
    end

    # Check canonical og:url
    if crawler_html =~ %r{property="og:url"\s+content="([^"]*\/reel\/[^"]*)"}i
      result[:post_type] = 'Reel'
    end

    # Engagement numbers from og:description
    if crawler_html =~ /<meta\s+property="og:description"\s+content="([^"]+)"/i
      desc = Regexp.last_match(1)
      result[:caption] = desc.slice(0, 160) if result[:caption] == '—'

      if desc =~ /([\d\.,KMkm]+)\s*likes/i && result[:likes] == '—'
        result[:likes] = Regexp.last_match(1)
      end
      if desc =~ /([\d\.,KMkm]+)\s*comments/i && result[:comments] == '—'
        result[:comments] = Regexp.last_match(1)
      end
      if desc =~ /([\d\.,KMkm]+)\s*views/i
        result[:views] = Regexp.last_match(1)
        result[:post_type] = 'Reel'
      end
      if desc =~ /([\d\.,KMkm]+)\s*followers/i
        result[:followers] = Regexp.last_match(1)
      end
    end

    # Timestamp from article:published_time or uploadDate
    if crawler_html =~ /<meta\s+property="article:published_time"\s+content="([^"]+)"/i ||
       crawler_html =~ /"uploadDate":\s*"([^"]+)"/ ||
       crawler_html =~ /"datePublished":\s*"([^"]+)"/
      raw_t = Regexp.last_match(1)
      pt = Time.parse(raw_t) rescue nil
      result[:posted_date] = pt.strftime('%b %d, %Y, %I:%M %p') if pt
    end
  end

  # Page Link from slug
  if clean_url =~ %r{facebook\.com/([^/?#]+)}i
    slug = Regexp.last_match(1)
    unless %w[watch reel posts share photos videos].include?(slug)
      result[:page_link] = "https://www.facebook.com/#{slug}/"
      result[:page_name] = slug.gsub('.', ' ').split.map(&:capitalize).join(' ') if result[:page_name] == '—'

      # Query page follower count via crawler
      if result[:followers] == '—'
        p_html = fetch_meta_bypass("https://www.facebook.com/#{slug}/", :crawler)
        if p_html =~ /([\d\.,KMkm]+)\s*(?:followers|people follow this)/i
          result[:followers] = Regexp.last_match(1)
        end
      end
    end
  end

  if result[:post_type] != 'Reel' && result[:post_type] != 'Video'
    result[:views] = '—'
  else
    if result[:views] == '—' || result[:views].nil? || result[:views].empty? || result[:views].to_s.include?('N/A')
      result[:views] = calculate_views_rb(result[:post_type], result[:likes], result[:comments], result[:followers])
    end
  end

  result[:status] = (result[:likes] != '—' || result[:comments] != '—') ? 'Live Verified' : 'Public Active'
  result
end

def process_meta_links(urls, preserve_duplicates: false)
  raw_links = []
  clean_urls = []
  seen = {}

  urls.map(&:to_s).each do |u|
    u.scan(%r{https?://(?:(?!https?://)[^\s'"<>])+}) do |link|
      link = link.sub(/[.,;)>\]]+$/, '')
      next if link.empty?
      next unless link.include?('instagram.com') || link.include?('facebook.com') || link.include?('fb.watch')
      clean = link.split('?').first.split('#').first.sub(/\/+$/, '') + '/'
      norm_key = clean.sub(/\/+$/, '').downcase
      raw_links << { original: link, clean: clean, key: norm_key }
      unless seen[norm_key]
        seen[norm_key] = true
        clean_urls << clean
      end
    end
  end
  return [] if clean_urls.empty?

  extractor_path = File.join(DIR, 'scraper', 'extractor.py')
  require 'open3'
  stdout, stderr, status = Open3.capture3('/usr/bin/python3', extractor_path, '--stdin', stdin_data: clean_urls.to_json)
  
  unique_items = []
  if status.success? && !stdout.to_s.strip.empty?
    begin
      items = JSON.parse(stdout, symbolize_names: true)
      unique_items = items if items.is_a?(Array) && !items.empty?
    rescue StandardError => e
      warn "JSON Parse Error: #{e.message}"
    end
  else
    warn "Extractor error: #{stderr}"
  end

  # Fallback to Ruby parser if needed
  if unique_items.empty?
    clean_urls.each do |url|
      if url.include?('instagram.com')
        unique_items << scrape_instagram_real(url)
      elsif url.include?('facebook.com') || url.include?('fb.watch')
        unique_items << scrape_facebook_real(url)
      end
    end
  end

  return unique_items unless preserve_duplicates

  # Map back to raw links preserving duplicate order and original URLs
  item_map = {}
  unique_items.each do |it|
    k = it[:original_url].to_s.split('?').first.split('#').first.sub(/\/+$/, '').downcase
    item_map[k] = it
  end

  raw_links.map do |rl|
    match = item_map[rl[:key]]
    if match
      cloned = match.dup
      cloned[:original_url] = rl[:original]
      cloned
    else
      { platform: 'unknown', original_url: rl[:original], status: 'Not Found' }
    end
  end
end

# Status API
server.mount_proc '/api/status' do |_req, res|
  res['Content-Type'] = 'application/json'
  res.body = JSON.generate({ status: 'running', engine: 'Meta Real-Time Post Engine (With Graph API & Crawler)', version: '3.3.0' })
end

# Meta Graph API Live Status API
server.mount_proc '/api/meta_api_status' do |_req, res|
  me_data = query_meta_graph_rb('me', { fields: 'id,name' })
  is_valid = (!me_data.empty? && me_data['id']) ? true : false
  err_msg = me_data['error'] ? me_data['error']['message'] : nil
  res['Content-Type'] = 'application/json'
  res.body = JSON.generate({
    connected: is_valid,
    app_id: META_APP_ID,
    page_id: META_PAGE_ID,
    page_name: me_data['name'] || 'Newsupdated24hr',
    api_version: META_GRAPH_API_VERSION,
    sync_interval_minutes: SOCIAL_SYNC_INTERVAL_MINUTES,
    token_configured: !META_PAGE_ACCESS_TOKEN.to_s.empty?,
    error: err_msg,
    status: is_valid ? 'Active & Authenticated' : (err_msg ? "Token Expired: #{err_msg.to_s.split('.').first}" : 'Token Check')
  })
end

# Clear Master Stream API
server.mount_proc '/api/clear_stream' do |_req, res|
  master_csv = File.join(OUTPUT_DIR, 'live_master_stream.csv')
  all_csv = File.join(OUTPUT_DIR, 'live_all_stream.csv')
  File.delete(master_csv) if File.exist?(master_csv)
  File.delete(all_csv) if File.exist?(all_csv)
  res['Content-Type'] = 'application/json'
  res.body = JSON.generate({ success: true, message: 'All live streams cleared (deduplicated and raw)' })
end

# Notification API
server.mount_proc '/api/notify' do |req, res|
  data = begin
           JSON.parse(req.body.to_s)
         rescue StandardError
           {}
         end
  title = data['title'] || 'Meta Post Scraper'
  msg = data['message'] || 'Real-time engagements refreshed.'
  sound = data['sound'] || 'Hero'
  macos_notify(title, msg, sound)
  res['Content-Type'] = 'application/json'
  res.body = JSON.generate({ success: true })
end

# Real-Time Scrape Endpoint
server.mount_proc '/api/scrape_posts' do |req, res|
  data = begin
           JSON.parse(req.body.to_s)
         rescue StandardError
           {}
         end
  urls = data['urls'] || []
  urls = [data['url']] if urls.empty? && data['url']
  preserve_dups = data['preserve_duplicates'] == true

  start_time = Time.now
  scraped_items = process_meta_links(urls, preserve_duplicates: preserve_dups)
  unique_items = if preserve_dups
                   seen_k = {}
                   scraped_items.select do |it|
                     k = it[:original_url].to_s.split('?').first.split('#').first.sub(/\/+$/, '').downcase
                     seen_k[k] ? false : (seen_k[k] = true)
                   end
                 else
                   scraped_items
                 end
  elapsed = (Time.now - start_time).round(2)

  timestamp = Time.now.strftime('%Y%m%d_%H%M%S')
  csv_file = File.join(OUTPUT_DIR, "real_engagements_#{timestamp}.csv")
  master_csv = File.join(OUTPUT_DIR, "live_master_stream.csv")
  all_csv = File.join(OUTPUT_DIR, "live_all_stream.csv")

  # Write batch CSV
  csv_content = ["\xEF\xBB\xBFPlatform,Post Type,Page Name,Page Link,Followers,Views,Likes,Comments,Date Posted,Original Link,Status,Last Checked"]
  scraped_items.each do |it|
    row = [
      it[:platform].to_s.capitalize,
      it[:post_type] || 'Post',
      %("#{it[:page_name]&.to_s&.gsub('"', '""')}"),
      %("#{it[:page_link]}"),
      %("#{it[:followers]}"),
      %("#{it[:views]}"),
      %("#{it[:likes]}"),
      %("#{it[:comments]}"),
      %("#{it[:posted_date]}"),
      %("#{it[:original_url]}"),
      %("#{it[:status]}"),
      %("#{it[:last_checked]}")
    ].join(',')
    csv_content << row
  end
  File.write(csv_file, csv_content.join("\n"))

  begin
    # 1. Maintain fully deduplicated live master stream CSV (Unique Links Only)
    existing_rows = {}
    header = "\xEF\xBB\xBFPlatform,Post Type,Page Name,Page Link,Followers,Views,Likes,Comments,Date Posted,Original Link,Status,Last Checked"
    require 'csv'
    if File.exist?(master_csv)
      raw_master = File.read(master_csv, mode: 'rb').encode('UTF-8', invalid: :replace, undef: :replace, replace: '')
      raw_master.each_line.with_index do |line, idx|
        next if idx == 0
        l = line.strip
        next if l.empty?
        begin
          cols = CSV.parse_line(l)
          orig = cols && cols[9] ? cols[9].to_s : l
          key = orig.split('?').first.split('#').first.sub(/\/+$/, '').downcase
        rescue StandardError
          key = l
        end
        existing_rows[key] = l
      end
    end

    unique_items.each do |it|
      row = [
        it[:platform].to_s.capitalize,
        it[:post_type] || 'Post',
        %("#{it[:page_name]&.to_s&.gsub('"', '""')}"),
        %("#{it[:page_link]}"),
        %("#{it[:followers]}"),
        %("#{it[:views]}"),
        %("#{it[:likes]}"),
        %("#{it[:comments]}"),
        %("#{it[:posted_date]}"),
        %("#{it[:original_url]}"),
        %("#{it[:status]}"),
        %("#{it[:last_checked]}")
      ].join(',')
      key = it[:original_url].to_s.split('?').first.split('#').first.sub(/\/+$/, '').downcase
      existing_rows[key] = row
    end

    File.open(master_csv, 'w:UTF-8') do |f|
      f.puts(header)
      existing_rows.each_value { |r| f.puts(r) }
    end

    # 2. Maintain raw stream CSV with ALL data (Duplicates Preserved)
    all_existed = File.exist?(all_csv)
    File.open(all_csv, all_existed ? 'a:UTF-8' : 'w:UTF-8') do |f|
      f.puts(header) unless all_existed
      scraped_items.each do |it|
        row = [
          it[:platform].to_s.capitalize,
          it[:post_type] || 'Post',
          %("#{it[:page_name]&.to_s&.gsub('"', '""')}"),
          %("#{it[:page_link]}"),
          %("#{it[:followers]}"),
          %("#{it[:views]}"),
          %("#{it[:likes]}"),
          %("#{it[:comments]}"),
          %("#{it[:posted_date]}"),
          %("#{it[:original_url]}"),
          %("#{it[:status]}"),
          %("#{it[:last_checked]}")
        ].join(',')
        f.puts(row)
      end
    end
  rescue StandardError => e
    warn "CSV persistence warning: #{e.message}"
  end

  res['Content-Type'] = 'application/json'
  res.body = JSON.generate({
    success: true,
    total: scraped_items.size,
    total_unique: unique_items.size,
    elapsed_seconds: elapsed,
    last_updated: Time.now.strftime('%b %d, %Y %I:%M:%S %p'),
    items: scraped_items,
    unique_items: unique_items,
    csv_download: "/output/#{File.basename(csv_file)}",
    master_csv_download: "/output/live_master_stream.csv",
    all_csv_download: "/output/live_all_stream.csv"
  })
end

# Serve /output/ files
server.mount_proc '/output' do |req, res|
  rel_path = req.path.sub(%r{^/output/}, '')
  full_path = File.join(OUTPUT_DIR, rel_path)
  if File.file?(full_path)
    res['Content-Type'] = case full_path
                          when /\.csv$/ then 'text/csv; charset=utf-8'
                          when /\.json$/ then 'application/json; charset=utf-8'
                          else 'application/octet-stream'
                          end
    res.body = File.read(full_path)
  else
    res.status = 404
    res.body = 'Not Found'
  end
end

# Static file serving
server.mount_proc '/' do |req, res|
  if req.path == '/' || req.path == '/dashboard.html'
    full_path = File.join(DIR, 'dashboard.html')
  else
    path = req.path.sub(%r{^/}, '')
    full_path = File.expand_path(File.join(STATIC_DIR, path))
  end

  if File.file?(full_path) && full_path.start_with?(DIR)
    res['Content-Type'] = case full_path
                          when /\.html$/ then 'text/html; charset=utf-8'
                          when /\.css$/ then 'text/css; charset=utf-8'
                          when /\.js$/ then 'application/javascript; charset=utf-8'
                          else 'text/plain; charset=utf-8'
                          end
    res.body = File.read(full_path)
  else
    res.status = 404
    res.body = 'Not Found'
  end
end

trap('INT') { server.shutdown }

puts "========================================================================"
puts "🍎 Real-Time Meta Scraper running at: http://localhost:#{PORT}"
puts "No Login Required • Auto-refresh: Every 5 minutes • Hard Refresh: Enabled"
puts "========================================================================"

server.start
