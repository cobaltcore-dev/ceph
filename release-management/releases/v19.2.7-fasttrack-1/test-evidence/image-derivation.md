# Image derivation: source_repository label

A customer policy requires the configuration label `source_repository`. The tested image did
not have this label. We added the label to the tested image and changed nothing else. We did
not rebuild the image. Later builds will set the label in the build system.

## Images

- Tested: `harbor.clyso.com/c-customers/cobaltcore/ceph/ceph@sha256:a874fec72c5b64be6c0c0f47a0b6a4d3cbb12d4c7c1ffc457593a86ce732ebce`
- Delivered: `harbor.clyso.com/c-customers/cobaltcore/ceph/ceph@sha256:5123bac4cbc7ac2af1183cf20d0956882869a11118a22b505f6ea60f2dad8895`

The tag `19.2.7-fasttrack-1-rc3` first pointed to the tested image. It now points to the
delivered image. Use the digests, not the tag. All test evidence in this directory applies to
the tested image.

## Change

The image configuration has one new label:

```json
"source_repository": "https://github.com/cobaltcore-dev/ceph.git"
```

The new configuration has a new digest, so the manifest also has a new digest. The layer
`sha256:ed38719aa5bf2f3b2b24f4bb5ea301fd6588f6421d957db519354febe5a363f3` and all manifest
annotations did not change. The annotations still show the rc3 values.

## How to make sure that only the label changed

You need skopeo, jq, and read access to the registry. Run these commands:

```sh
T=docker://harbor.clyso.com/c-customers/cobaltcore/ceph/ceph@sha256:a874fec72c5b64be6c0c0f47a0b6a4d3cbb12d4c7c1ffc457593a86ce732ebce
D=docker://harbor.clyso.com/c-customers/cobaltcore/ceph/ceph@sha256:5123bac4cbc7ac2af1183cf20d0956882869a11118a22b505f6ea60f2dad8895
diff <(skopeo inspect --raw $T | jq -S 'del(.config.digest,.config.size)') \
     <(skopeo inspect --raw $D | jq -S 'del(.config.digest,.config.size)') && echo manifest-ok
diff <(skopeo inspect --config $T | jq -S 'del(.config.Labels.source_repository)') \
     <(skopeo inspect --config $D | jq -S 'del(.config.Labels.source_repository)') && echo config-ok
```

If the first command prints `manifest-ok`, the two images have the same layers and annotations.
If the second command prints `config-ok`, the label is the only change in the configuration.

The release engineer ran these commands and got this output:

```text
manifest-ok
config-ok
```
