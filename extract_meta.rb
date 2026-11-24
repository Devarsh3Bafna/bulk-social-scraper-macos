#!/usr/bin/env ruby
# frozen_string_literal: true
# ==============================================================================
# CLI Runner: Original Facebook & Instagram Real Engagement Scraper
# Usage: ./extract_meta.rb "https://www.instagram.com/reel/..." "https://facebook.com/..."
# ==============================================================================

require 'json'
require 'open3'

urls = ARGV
if urls.empty?
  puts "Usage: #{$PROGRAM_NAME} <facebook_or_instagram_post_urls...>"
  puts "Example: #{$PROGRAM_NAME} https://www.instagram.com/reel/DePI-TbRKO3/"
  exit 1
end

puts "========================================================================"
puts "🍎 Extracting Real Engagements for #{urls.size} Post(s)..."
puts "========================================================================"

extractor_path = File.join(__dir__, 'scraper', 'extractor.py')
stdout, stderr, status = Open3.capture3('/usr/bin/python3', extractor_path, *urls)

unless status.success? && !stdout.to_s.strip.empty?
  warn "Error executing extractor: #{stderr}"
  exit 1
end

results = JSON.parse(stdout, symbolize_names: true) rescue []

results.each_with_index do |item, idx|
  puts "\n[#{idx + 1}/#{results.size}] Platform: #{item[:platform].to_s.upcase}"
  puts "  • Page Name:       #{item[:page_name]}"
  puts "  • Page Link:       #{item[:page_link]}"
  puts "  • Followers:       #{item[:followers]}"
  puts "  • Views:           #{item[:views]}"
  puts "  • Likes:           #{item[:likes]}"
  puts "  • Comments:        #{item[:comments]}"
  puts "  • Posted Date:     #{item[:posted_date]}"
  puts "  • Live Status:     #{item[:status]}"
  puts "  • Original Link:   #{item[:original_url]}"
end
puts "\nDone. Verified at #{Time.now.strftime('%I:%M:%S %p')}."
