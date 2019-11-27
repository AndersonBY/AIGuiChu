# -*- coding: utf-8 -*-
# @Author: Anderson
# @Date:   2019-11-26 17:22:56
# @Last Modified by:   ander
# @Last Modified time: 2019-11-27 21:45:52
from moviepy.editor import VideoFileClip, ColorClip, CompositeVideoClip, AudioFileClip
import moviepy.video.fx.all as vfx
from moviepy.video.fx.mask_color import mask_color
import time
import json


def tiktok_effect(frame):
	# 单独抽取去掉红色通道的图像
	gb_channel_frame = frame.copy()
	gb_channel_frame[:, :, 0].fill(0)

	# 单独抽取红色通道图像
	r_channel_frame = frame.copy()
	r_channel_frame[:, :, 1].fill(0)
	r_channel_frame[:, :, 2].fill(0)

	# 错位合并图像，形成抖音效果
	result = frame.copy()
	result[:-5, :-5, :] = r_channel_frame[:-5, :-5, :] + gb_channel_frame[5:, 5:, :]

	return result


def person_mask_effect(roi_clip, mask_clip, current_time, clip_start_time, clip_end_time):
	clip_duration = clip_end_time - clip_start_time
	red_clip = ColorClip(roi_clip.size, (255, 0, 0), duration=clip_duration)
	blue_clip = ColorClip(roi_clip.size, (0, 0, 255), duration=clip_duration)

	roi_clip = roi_clip.subclip(clip_start_time, clip_end_time)
	mask_clip = mask_clip.subclip(clip_start_time, clip_end_time)

	person_clip_height = int(HEIGHT * 0.9)

	center_person_clip = (
		roi_clip.fl_image(tiktok_effect)
		.set_mask(mask_clip)
		.resize(height=person_clip_height)
		.set_pos(("center", "center"))
		.set_start(current_time)
	)
	left_person_clip = (
		red_clip.set_mask(mask_clip)
		.resize(height=person_clip_height)
		.set_opacity(0.5)
		.set_start(current_time)
	)
	right_person_clip = (
		blue_clip.set_mask(mask_clip)
		.resize(height=person_clip_height)
		.set_opacity(0.5)
		.set_start(current_time)
	)

	left_person_clip_x = (WIDTH / 2 - left_person_clip.w / 2) - int(
		left_person_clip.w * 0.3
	)
	right_person_clip_x = (WIDTH / 2 - left_person_clip.w / 2) + int(
		left_person_clip.w * 0.3
	)
	person_clip_y = HEIGHT / 2 - left_person_clip.h / 2

	left_person_clip = left_person_clip.set_pos((left_person_clip_x, person_clip_y))
	right_person_clip = right_person_clip.set_pos((right_person_clip_x, person_clip_y))

	return [left_person_clip, right_person_clip, center_person_clip]


def pure_color_person_mask_effect(roi_clip, mask_clip, current_time, clip_start_time, clip_end_time):
	clip_duration = clip_end_time - clip_start_time
	white_clip = ColorClip(SIZE, (255, 255, 255), duration=clip_duration)

	mask_clip = mask_clip.subclip(clip_start_time, clip_end_time)

	person_clip_height = int(HEIGHT * 0.9)

	center_person_clip = (
		white_clip
		.set_mask(mask_clip.resize(height=person_clip_height))
		.set_pos(("center", "center"))
		.set_start(current_time)
	)

	background_color_clip = ColorClip(
		SIZE, (80, 40, 255), duration=clip_duration
	).set_start(current_time)

	return [
		CompositeVideoClip([background_color_clip, center_person_clip]).fl_image(
			tiktok_effect
		)
	]


with open('config.json', 'r', encoding='utf-8') as f:
	CONFIGS = json.load(f)
	WIDTH, HEIGHT = CONFIGS['width'], CONFIGS['height']
	SIZE = (WIDTH, HEIGHT)
	PURE_COLOR_EFFECT_TIMES = CONFIGS['special times']
	PERSON_CLIPS_FILENAMES = CONFIGS['person clip files']
	BACKGROUND_MUSIC = CONFIGS['bgm']
	BACKGROUND_VIDEO = CONFIGS['background video']

background_music = AudioFileClip(BACKGROUND_MUSIC)
final_clip_duration = background_music.duration

composite_clips = []
pure_color_effect_clips = []
current_time = 0

for person_clip_filename in PERSON_CLIPS_FILENAMES:
	roi_clip_filename = ".".join(person_clip_filename.split(".")[:-1]) + "_roi.avi"
	mask_clip_filename = ".".join(person_clip_filename.split(".")[:-1]) + "_mask.avi"

	roi_clip = VideoFileClip(roi_clip_filename).without_audio()
	mask_clip = (
		mask_color(VideoFileClip(mask_clip_filename), color=[255, 255, 255])
		.fx(vfx.loop, duration=roi_clip.duration)
		.to_mask()
	)

	clip_duration = roi_clip.duration

	person_mask_effect_clips = person_mask_effect(roi_clip, mask_clip, current_time, 0, clip_duration)
	composite_clips.extend(person_mask_effect_clips)
	pure_color_person_mask_effect_clips = pure_color_person_mask_effect(
		roi_clip, mask_clip, current_time, 0, clip_duration
	)
	pure_color_effect_clips.extend(pure_color_person_mask_effect_clips)
	current_time += clip_duration

pure_color_effect_clip = CompositeVideoClip(pure_color_effect_clips).fx(vfx.loop, duration=final_clip_duration)
pure_color_effect_subclips = []
for start_time, end_time in PURE_COLOR_EFFECT_TIMES:
	if start_time < final_clip_duration:
		subclip = pure_color_effect_clip.subclip(start_time, end_time).set_start(start_time)
		pure_color_effect_subclips.append(subclip)
	else:
		break
pure_color_effect_subclip = CompositeVideoClip(pure_color_effect_subclips)

background_clip = (
	VideoFileClip(BACKGROUND_VIDEO)
	.without_audio()
	.resize(SIZE)
	.fx(vfx.loop, duration=final_clip_duration)
)

composite_clips.insert(0, background_clip)

loop_clip = CompositeVideoClip(composite_clips).set_duration(
	min(current_time, final_clip_duration)
)
loop_clip_path = f'./Temp/{time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())}.mp4'
loop_clip.write_videofile(
	loop_clip_path,
	fps=30,
	codec='mpeg4',
	bitrate="8000k",
	threads=4,
)

loop_clip = VideoFileClip(loop_clip_path).fx(vfx.loop, duration=final_clip_duration)
final_clip = CompositeVideoClip([loop_clip, pure_color_effect_subclip])
final_clip = final_clip.set_audio(background_music).set_duration(final_clip_duration)
final_clip.write_videofile(
	f'./output/{time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime())}.mp4',
	fps=30,
	codec='mpeg4',
	bitrate="8000k",
	audio_codec="libmp3lame",
	threads=4,
)
