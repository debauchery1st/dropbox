#!/usr/bin/env python

from __future__ import with_statement
from StringIO import StringIO
import unittest
import os
import posixpath
import sys
from uuid import UUID
from dropbox import session, client, rest
import datetime
from dropbox.rest import ErrorResponse


class BaseClientTests(object):

    @classmethod
    def setUpClass(cls):
        """Creates the API client and decides on a test directory."""
        app_key, app_secret = cls.app_key, cls.app_secret

        sess = cls.Session(app_key, app_secret)
        cls._configure_session(sess)

        cls.client = client.DropboxClient(sess)
        cls.test_dir = "/" + \
            datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        here = os.path.abspath(os.path.dirname(sys.argv[0]))
        cls.foo = os.path.join(here, "../testfiles/foo.txt")
        cls.frog = os.path.join(here, "../testfiles/Costa Rican Frog.jpg")
        cls.song = os.path.join(here, "../testfiles/dropbox_song.mp3")

    @classmethod
    def tearDownClass(cls):
        cls.client.file_delete(cls.test_dir)

    def upload_file(self, src, target, **kwargs):
        f = open(src, "rb")
        self.client.put_file(target, f, **kwargs)

    def dict_has(self, dictionary, *args, **kwargs):
        """Convenience method to check if a dictionary contains the specified
        keys and key-value pairs"""
        for key in args:
            self.assertTrue(key in dictionary)
        for (key, value) in kwargs.items():
            self.assertEqual(value, dictionary[key])

    def assert_file(self, dictionary, filename, *args, **kwargs):
        import os
        defaults = dict(
            bytes=os.path.getsize(filename),
            is_dir=False
        )
        combined = dict(defaults.items() + kwargs.items())
        self.dict_has(dictionary, *args,
                      **combined
                      )

    def test_account_info(self):
        """Tests if the account_info returns the expected fields."""
        account_info = self.client.account_info()
        self.dict_has(account_info,
                      "country",
                      "display_name",
                      "referral_link",
                      "quota_info",
                      "uid"
                      )

    def test_put_file(self):
        """Tests if put_file returns the expected metadata"""
        def test_put(file, path):
            file_path = posixpath.join(self.test_dir, path)
            f = open(file, "rb")
            metadata = self.client.put_file(file_path, f)
            self.assert_file(metadata, file, path=file_path)
        test_put(self.foo, "put_foo.txt")
        test_put(self.song, "put_song.mp3")
        test_put(self.frog, "put_frog.jpg")

    def test_put_file_overwrite(self):
        """Tests if put_file with overwrite=true returns the expected metadata"""
        path = posixpath.join(self.test_dir, "foo_overwrite.txt")
        self.upload_file(self.foo, path)
        f = StringIO("This Overwrites")
        metadata = self.client.put_file(path, f, overwrite=True)
        self.dict_has(metadata,
                      size="15 bytes",
                      bytes=15,
                      is_dir=False,
                      path=path,
                      mime_type="text/plain"
                      )

    def test_get_file(self):
        """Tests if storing and retrieving a file returns the same file"""
        def test_get(file, path):
            file_path = posixpath.join(self.test_dir, path)
            self.upload_file(file, file_path)
            downloaded = self.client.get_file(file_path).read()
            local = open(file, "rb").read()
            self.assertEqual(len(downloaded), len(local))
            self.assertEqual(downloaded, local)
        test_get(self.foo, "get_foo.txt")
        test_get(self.frog, "get_frog.txt")
        test_get(self.song, "get_song.txt")

    def test_metadata(self):
        """Tests if metadata returns the expected values for a files uploaded earlier"""
        path = posixpath.join(self.test_dir, "foo_upload.txt")
        self.upload_file(self.foo, path)
        metadata = self.client.metadata(path)
        self.assert_file(metadata, self.foo, path=path)

    def test_metadata_bad(self):
        """Tests if metadata returns an error for nonexistent file"""
        self.assertRaises(
            ErrorResponse,
            lambda: self.client.metadata(
                posixpath.join(self.test_dir, "foo_does_not_exist.txt"))
        )

    def test_create_folder(self):
        """Tests if creating a folder works"""
        path = posixpath.join(self.test_dir, "new_folder")
        metadata = self.client.file_create_folder(path)
        self.dict_has(metadata,
                      size="0 bytes",
                      bytes=0,
                      is_dir=True,
                      path=path
                      )

    def test_create_folder_dupe(self):
        """Tests if creating a folder fails correctly if one already exists"""
        path = posixpath.join(self.test_dir, "new_folder_dupe")
        metadata = self.client.file_create_folder(path)
        self.assertRaises(
            ErrorResponse,
            lambda: self.client.file_create_folder(path)
        )

    def test_delete(self):
        """Tests if deleting a file really makes it disappear"""
        path = posixpath.join(self.test_dir, "delfoo.txt")
        self.upload_file(self.foo, path)
        metadata = self.client.metadata(path)
        self.assert_file(metadata, self.foo, path=path)
        self.client.file_delete(path)

        metadata = self.client.metadata(path)
        self.assert_file(metadata, self.foo,
                         path=path,
                         bytes=0,
                         size="0 bytes",
                         is_deleted=True
                         )

    def test_copy(self):
        """Tests copying a file, to ensure that two copies exist after the operation"""
        path = posixpath.join(self.test_dir, "copyfoo.txt")
        path2 = posixpath.join(self.test_dir, "copyfoo2.txt")
        self.upload_file(self.foo, path)
        self.client.file_copy(path, path2)
        metadata = self.client.metadata(path)
        metadata2 = self.client.metadata(path2)
        self.assert_file(metadata, self.foo, path=path)
        self.assert_file(metadata2, self.foo, path=path2)

    def test_move(self):
        """"Tests moving a file, to ensure the new copy exists and the old copy is removed"""
        path = posixpath.join(self.test_dir, "movefoo.txt")
        path2 = posixpath.join(self.test_dir, "movefoo2.txt")
        self.upload_file(self.foo, path)
        self.client.file_move(path, path2)

        metadata = self.client.metadata(path)
        self.assert_file(metadata, self.foo, path=path,
                         is_deleted=True, size="0 bytes", bytes=0)

        metadata = self.client.metadata(path2)
        self.assert_file(metadata, self.foo, path=path2)

    def test_stream(self):
        """Tests file streaming using the /media endpoint"""
        path = posixpath.join(self.test_dir, "stream_song.mp3")
        self.upload_file(self.song, path)
        link = self.client.media(path)
        self.dict_has(link,
                      "url",
                      "expires"
                      )

    def test_share(self):
        """Tests file streaming using the /media endpoint"""
        path = posixpath.join(self.test_dir, "stream_song.mp3")
        self.upload_file(self.song, path)
        link = self.client.share(path)
        self.dict_has(link,
                      "url",
                      "expires"
                      )

    def test_search(self):
        """Tests searching for a file in a folder"""
        path = posixpath.join(self.test_dir, "search/")

        j = posixpath.join
        self.upload_file(self.foo, j(path, "text.txt"))
        self.upload_file(self.foo, j(path, "subFolder/text.txt"))
        self.upload_file(self.foo, j(path, "subFolder/cow.txt"))
        self.upload_file(self.frog, j(path, "frog.jpg"))
        self.upload_file(self.frog, j(path, "frog2.jpg"))
        self.upload_file(self.frog, j(path, "subFolder/frog2.jpg"))

        results = self.client.search(path, "sasdfasdf")
        self.assertEquals(results, [])
        results = self.client.search(path, "jpg")
        self.assertEquals(len(results), 3)
        for metadata in results:
            self.assert_file(metadata, self.frog)

        results = self.client.search(j(path, "subFolder"), "jpg")
        self.assertEquals(len(results), 1)
        self.assert_file(results[0], self.frog)

    def test_revisions_restore(self):
        """Tests getting the old revisions of a file"""
        path = posixpath.join(self.test_dir, "foo_revs.txt")
        self.upload_file(self.foo, path)
        self.upload_file(self.frog, path, overwrite=True)
        self.upload_file(self.song, path, overwrite=True)
        revs = self.client.revisions(path)
        metadata = self.client.metadata(path)
        self.assert_file(
            metadata, self.song, path=path, mime_type="text/plain")

        self.assertEquals(len(revs), 3)
        self.assert_file(
            revs[0], self.song, path=path, mime_type="text/plain")
        self.assert_file(
            revs[1], self.frog, path=path, mime_type="text/plain")
        self.assert_file(
            revs[2], self.foo, path=path, mime_type="text/plain")

        metadata = self.client.restore(path, revs[2]["rev"])
        self.assert_file(
            metadata, self.foo, path=path, mime_type="text/plain")
        metadata = self.client.metadata(path)
        self.assert_file(
            metadata, self.foo, path=path, mime_type="text/plain")

    def test_copy_ref(self):
        """Tests using the /copy_ref endpoint to move data within a single dropbox"""
        path = posixpath.join(self.test_dir, "foo_copy_ref.txt")
        path2 = posixpath.join(self.test_dir, "foo_copy_ref_target.txt")

        self.upload_file(self.foo, path)
        copy_ref = self.client.create_copy_ref(path)
        self.dict_has(copy_ref,
                      "expires",
                      "copy_ref"
                      )

        self.client.add_copy_ref(copy_ref["copy_ref"], path2)
        metadata = self.client.metadata(path2)
        self.assert_file(metadata, self.foo, path=path2)
        copied_foo = self.client.get_file(path2).read()
        local_foo = open(self.foo, "rb").read()
        self.assertEqual(len(copied_foo), len(local_foo))
        self.assertEqual(copied_foo, local_foo)

    def test_chunked_upload(self):
        path = posixpath.join(self.test_dir, "chunked_upload_file.txt")
        size = 1024 * 1024 * 10
        chunk_size = 4 * 1024 * 1102
        random_data = os.urandom(size)
        uploader = self.client.get_chunked_uploader(
            StringIO(random_data), size)
        error_count = 0
        while uploader.offset < size and error_count < 5:
            try:
                upload = uploader.upload_chunked(chunk_size=chunk_size)
            except rest.ErrorResponse as e:
                error_count += 1

        uploader.finish(path)
        downloaded = self.client.get_file(path).read()
        self.assertEquals(size, len(downloaded))
        self.assertEquals(random_data, downloaded)


class TestClientOAuth1(BaseClientTests, unittest.TestCase):
    Session = session.DropboxSession

    @classmethod
    def _configure_session(cls, sess):
        sess.set_token(cls.access_key, cls.access_secret)


class TestClientOAuth2(BaseClientTests, unittest.TestCase):
    Session = session.DropboxSessionOAuth2

    @classmethod
    def _configure_session(cls, sess):
        sess.set_token(cls.access_token)


if __name__ == '__main__':
    BaseClientTests.app_key = sys.argv[1]
    BaseClientTests.app_secret = sys.argv[2]
    TestClientOAuth1.access_key = sys.argv[3]
    TestClientOAuth1.access_secret = sys.argv[4]
    TestClientOAuth2.access_token = sys.argv[5]
    sys.argv[1:6] = []
    unittest.main()
