"""
Audio metadata helpers using mutagen.
Supports MP3 (ID3), FLAC, MP4/AAC (M4A), and OGG Vorbis.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def read_audio_metadata(filepath: str) -> dict:
    """
    Read audio metadata from a file using mutagen.

    Returns a dict with keys:
        title, artist, album, track_number, year,
        genre, composer, isrc, bpm, comment, duration_seconds

    Returns an empty dict on failure.
    """
    try:
        import mutagen
        from mutagen import File as MutagenFile
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.oggvorbis import OggVorbis

        path = Path(filepath)
        suffix = path.suffix.lower()

        audio = MutagenFile(filepath, easy=True)
        if audio is None:
            return {}

        duration_seconds = getattr(audio.info, 'length', None)

        data = {
            'duration_seconds': duration_seconds,
            'title': None,
            'artist': None,
            'album_artist': None,
            'album': None,
            'track_number': None,
            'disc_number': None,
            'year': None,
            'genre': None,
            'composer': None,
            'isrc': None,
            'bpm': None,
            'comment': None,
        }

        if suffix == '.mp3':
            # Use non-easy ID3 for full tag access
            from mutagen.id3 import ID3, ID3NoHeaderError
            try:
                tags = ID3(filepath)
            except ID3NoHeaderError:
                tags = {}

            def get_id3(tag_name):
                frame = tags.get(tag_name)
                if frame is None:
                    return None
                return str(frame) if not isinstance(frame, str) else frame

            data['title'] = get_id3('TIT2')
            data['artist'] = get_id3('TPE1')
            data['album_artist'] = get_id3('TPE2')
            data['album'] = get_id3('TALB')
            data['genre'] = get_id3('TCON')
            data['composer'] = get_id3('TCOM')
            data['isrc'] = get_id3('TSRC')
            data['year'] = get_id3('TDRC') or get_id3('TYER')

            bpm_frame = tags.get('TBPM')
            if bpm_frame:
                try:
                    data['bpm'] = int(str(bpm_frame))
                except (ValueError, TypeError):
                    pass

            trck = tags.get('TRCK')
            if trck:
                try:
                    data['track_number'] = int(str(trck).split('/')[0])
                except (ValueError, TypeError):
                    pass

            tpos = tags.get('TPOS')
            if tpos:
                try:
                    data['disc_number'] = int(str(tpos).split('/')[0])
                except (ValueError, TypeError):
                    pass

            comm = tags.get('COMM::eng') or tags.get('COMM:')
            if comm is None:
                # Try any COMM frame
                for key in tags.keys():
                    if key.startswith('COMM'):
                        comm = tags[key]
                        break
            if comm:
                data['comment'] = str(comm.text[0]) if hasattr(comm, 'text') else str(comm)

        elif suffix == '.flac':
            tags = FLAC(filepath)

            def get_flac(key):
                val = tags.get(key.lower()) or tags.get(key.upper())
                if val and len(val) > 0:
                    return val[0]
                return None

            data['title'] = get_flac('title')
            data['artist'] = get_flac('artist')
            data['album_artist'] = get_flac('albumartist') or get_flac('album artist')
            data['album'] = get_flac('album')
            data['genre'] = get_flac('genre')
            data['composer'] = get_flac('composer')
            data['isrc'] = get_flac('isrc')
            data['year'] = get_flac('date') or get_flac('year')
            data['comment'] = get_flac('comment')

            bpm_val = get_flac('bpm')
            if bpm_val:
                try:
                    data['bpm'] = int(bpm_val)
                except (ValueError, TypeError):
                    pass

            trck = get_flac('tracknumber')
            if trck:
                try:
                    data['track_number'] = int(str(trck).split('/')[0])
                except (ValueError, TypeError):
                    pass

            disc = get_flac('discnumber')
            if disc:
                try:
                    data['disc_number'] = int(str(disc).split('/')[0])
                except (ValueError, TypeError):
                    pass

        elif suffix in ('.m4a', '.mp4', '.aac'):
            tags = MP4(filepath)

            def get_mp4(key):
                val = tags.get(key)
                if val and len(val) > 0:
                    item = val[0]
                    return str(item) if not isinstance(item, str) else item
                return None

            data['title'] = get_mp4('\xa9nam')
            data['artist'] = get_mp4('\xa9ART')
            data['album_artist'] = get_mp4('aART')
            data['album'] = get_mp4('\xa9alb')
            data['genre'] = get_mp4('\xa9gen')
            data['composer'] = get_mp4('\xa9wrt')
            data['year'] = get_mp4('\xa9day')
            data['comment'] = get_mp4('\xa9cmt')

            trkn = tags.get('trkn')
            if trkn and len(trkn) > 0:
                try:
                    data['track_number'] = int(trkn[0][0])
                except (ValueError, TypeError, IndexError):
                    pass

            disk = tags.get('disk')
            if disk and len(disk) > 0:
                try:
                    data['disc_number'] = int(disk[0][0])
                except (ValueError, TypeError, IndexError):
                    pass

            bpm_val = tags.get('tmpo')
            if bpm_val and len(bpm_val) > 0:
                try:
                    data['bpm'] = int(bpm_val[0])
                except (ValueError, TypeError):
                    pass

        elif suffix == '.ogg':
            tags = OggVorbis(filepath)

            def get_ogg(key):
                val = tags.get(key.lower()) or tags.get(key.upper())
                if val and len(val) > 0:
                    return val[0]
                return None

            data['title'] = get_ogg('title')
            data['artist'] = get_ogg('artist')
            data['album_artist'] = get_ogg('albumartist') or get_ogg('album artist')
            data['album'] = get_ogg('album')
            data['genre'] = get_ogg('genre')
            data['composer'] = get_ogg('composer')
            data['isrc'] = get_ogg('isrc')
            data['year'] = get_ogg('date') or get_ogg('year')
            data['comment'] = get_ogg('comment')

            bpm_val = get_ogg('bpm')
            if bpm_val:
                try:
                    data['bpm'] = int(bpm_val)
                except (ValueError, TypeError):
                    pass

            trck = get_ogg('tracknumber')
            if trck:
                try:
                    data['track_number'] = int(str(trck).split('/')[0])
                except (ValueError, TypeError):
                    pass

            disc = get_ogg('discnumber')
            if disc:
                try:
                    data['disc_number'] = int(str(disc).split('/')[0])
                except (ValueError, TypeError):
                    pass

        # Clean up None values and strip strings
        result = {}
        for key, value in data.items():
            if value is not None:
                if isinstance(value, str):
                    value = value.strip()
                    if value:
                        result[key] = value
                else:
                    result[key] = value

        return result

    except Exception as exc:
        logger.warning('read_audio_metadata failed for %s: %s', filepath, exc)
        return {}


def write_audio_metadata(filepath: str, track_instance) -> bool:
    """
    Write metadata from a Track model instance back to the audio file tags.

    Uses the album's artist display_name and album title.
    Returns True on success, False on failure.
    """
    try:
        from mutagen.mp3 import MP3
        from mutagen.flac import FLAC
        from mutagen.mp4 import MP4
        from mutagen.oggvorbis import OggVorbis

        path = Path(filepath)
        suffix = path.suffix.lower()

        track = track_instance
        album = track.album

        try:
            profile_name = album.artist.artist_profile.display_name
        except Exception:
            profile_name = album.artist.get_full_name() or album.artist.email

        # Use track-level artist override if set, otherwise fall back to profile name
        artist_name = track.artist or profile_name
        album_artist_name = track.album_artist or profile_name
        compilation_val = '1' if album.compilation else '0'

        # Load cover art bytes for embedding, if available
        cover_data = None
        cover_mime = 'image/jpeg'
        if album.cover_art:
            try:
                import mimetypes as _mt
                cover_path = album.cover_art.path
                mime, _ = _mt.guess_type(cover_path)
                cover_mime = mime or 'image/jpeg'
                with open(cover_path, 'rb') as f:
                    cover_data = f.read()
            except Exception:
                pass

        if suffix == '.mp3':
            from mutagen.id3 import (
                ID3, ID3NoHeaderError, TIT2, TPE1, TPE2, TALB, TRCK, TPOS,
                TCON, TCOM, TSRC, TBPM, TDRC, COMM, TCMP, APIC,
            )
            try:
                tags = ID3(filepath)
            except ID3NoHeaderError:
                tags = ID3()

            def set_text(frame_cls, value):
                if value:
                    tags[frame_cls.__name__] = frame_cls(encoding=3, text=[str(value)])

            set_text(TIT2, track.title)
            set_text(TPE1, artist_name)
            set_text(TPE2, album_artist_name)
            set_text(TALB, album.title)
            set_text(TCON, track.genre)
            set_text(TCOM, track.composer)
            set_text(TSRC, track.isrc)
            tags['TCMP'] = TCMP(encoding=3, text=[compilation_val])

            if track.track_number:
                tags['TRCK'] = TRCK(encoding=3, text=[str(track.track_number)])
            if track.disc_number:
                tags['TPOS'] = TPOS(encoding=3, text=[str(track.disc_number)])
            if track.bpm:
                tags['TBPM'] = TBPM(encoding=3, text=[str(track.bpm)])
            if album.release_year:
                tags['TDRC'] = TDRC(encoding=3, text=[str(album.release_year)])
            if track.comment:
                tags['COMM::eng'] = COMM(encoding=3, lang='eng', desc='', text=[track.comment])
            if cover_data:
                tags.delall('APIC')
                tags['APIC:'] = APIC(encoding=3, mime=cover_mime, type=3, desc='Cover', data=cover_data)

            tags.save(filepath)

        elif suffix == '.flac':
            tags = FLAC(filepath)

            if track.title:
                tags['title'] = [track.title]
            tags['artist'] = [artist_name]
            tags['albumartist'] = [album_artist_name]
            tags['album'] = [album.title]
            tags['compilation'] = [compilation_val]
            if track.genre:
                tags['genre'] = [track.genre]
            if track.composer:
                tags['composer'] = [track.composer]
            if track.isrc:
                tags['isrc'] = [track.isrc]
            if track.track_number:
                tags['tracknumber'] = [str(track.track_number)]
            if track.disc_number:
                tags['discnumber'] = [str(track.disc_number)]
            if track.bpm:
                tags['bpm'] = [str(track.bpm)]
            if album.release_year:
                tags['date'] = [str(album.release_year)]
            if track.comment:
                tags['comment'] = [track.comment]
            if cover_data:
                from mutagen.flac import Picture
                pic = Picture()
                pic.type = 3  # Cover (front)
                pic.mime = cover_mime
                pic.data = cover_data
                tags.clear_pictures()
                tags.add_picture(pic)

            tags.save()

        elif suffix in ('.m4a', '.mp4', '.aac'):
            tags = MP4(filepath)

            if track.title:
                tags['\xa9nam'] = [track.title]
            tags['\xa9ART'] = [artist_name]
            tags['aART'] = [album_artist_name]
            tags['\xa9alb'] = [album.title]
            tags['cpil'] = album.compilation
            if track.genre:
                tags['\xa9gen'] = [track.genre]
            if track.composer:
                tags['\xa9wrt'] = [track.composer]
            if track.track_number:
                tags['trkn'] = [(track.track_number, 0)]
            if track.disc_number:
                tags['disk'] = [(track.disc_number, 0)]
            if track.bpm:
                tags['tmpo'] = [track.bpm]
            if album.release_year:
                tags['\xa9day'] = [str(album.release_year)]
            if track.comment:
                tags['\xa9cmt'] = [track.comment]
            if cover_data:
                from mutagen.mp4 import MP4Cover
                mp4_fmt = MP4Cover.FORMAT_PNG if cover_mime == 'image/png' else MP4Cover.FORMAT_JPEG
                tags['covr'] = [MP4Cover(cover_data, imageformat=mp4_fmt)]

            tags.save()

        elif suffix == '.ogg':
            tags = OggVorbis(filepath)

            if track.title:
                tags['title'] = [track.title]
            tags['artist'] = [artist_name]
            tags['albumartist'] = [album_artist_name]
            tags['album'] = [album.title]
            tags['compilation'] = [compilation_val]
            if track.genre:
                tags['genre'] = [track.genre]
            if track.composer:
                tags['composer'] = [track.composer]
            if track.isrc:
                tags['isrc'] = [track.isrc]
            if track.track_number:
                tags['tracknumber'] = [str(track.track_number)]
            if track.disc_number:
                tags['discnumber'] = [str(track.disc_number)]
            if track.bpm:
                tags['bpm'] = [str(track.bpm)]
            if album.release_year:
                tags['date'] = [str(album.release_year)]
            if track.comment:
                tags['comment'] = [track.comment]

            tags.save()

        else:
            logger.warning('write_audio_metadata: unsupported format %s', suffix)
            return False

        return True

    except Exception as exc:
        logger.warning('write_audio_metadata failed for %s: %s', filepath, exc)
        return False
