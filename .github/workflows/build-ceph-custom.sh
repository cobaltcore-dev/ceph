name: Build Custom Ceph Image (with PRs)

on:
  workflow_dispatch:
    inputs:
      pr_numbers:
        description: 'List of PR numbers to apply (space separated, e.g., "55123 56789")'
        required: false
        type: string
      ceph_tag:
        description: 'Base Ceph Version'
        required: true
        default: 'v19.2.3'
      push_image:
        description: 'Push image to GitHub Packages?'
        type: boolean
        default: true

jobs:
  build-ceph:
    name: Build Ceph Squid
    runs-on: self-hosted  # MUST be a large runner (32GB+ RAM recommended)
    permissions:
      contents: read
      packages: write  # Required to push to ghcr.io

    steps:
      # --- 1. SETUP & CLEAN ---
      - name: Checkout Code
        uses: actions/checkout@v4
        with:
          ref: ${{ inputs.ceph_tag }}
          submodules: recursive
          fetch-depth: 0

      - name: Clean Workspace
        run: |
          git clean -fdx
          git submodule foreach --recursive git clean -fdx
          git submodule update --init --recursive

      # --- 2. APPLY PULL REQUESTS ---
      - name: Apply Custom PRs
        if: "${{ inputs.pr_numbers != '' }}"
        run: |
          PRS="${{ inputs.pr_numbers }}"
          echo "Applying PRs: $PRS"
          
          for PR in $PRS; do
            echo "Fetching PR #$PR..."
            git fetch origin pull/$PR/head:pr-$PR
            
            echo "Merging PR #$PR..."
            git config user.email "ci-bot@example.com"
            git config user.name "CI Bot"
            git merge --no-edit pr-$PR
          done
          git submodule update --init --recursive

      # --- 3. PATCH BUILDER ---
      - name: Patch Builder Script
        run: |
          sed -i 's/dnf install -y \/usr\/bin\/rpmbuild/dnf install -y --allowerasing \/usr\/bin\/rpmbuild/g' src/script/buildcontainer-setup.sh

      # --- 4. COMPILE CEPH ---
      - name: Compile RPMs
        run: |
          # Dynamic RAM allocation
          CORE_COUNT=$(nproc)
          MEM_GB=$(free -g | awk '/^Mem:/{print $2}')
          JOBS=$((MEM_GB / 2))
          [[ $JOBS -lt 2 ]] && JOBS=2
          [[ $JOBS -gt $CORE_COUNT ]] && JOBS=$CORE_COUNT
          export NINJAJOBS=$JOBS

          ./src/script/build-with-container.py \
            -d centos9 \
            -e rpm \
            -- \
            -DCMAKE_BUILD_TYPE=RelWithDebInfo \
            -DENABLE_LTO=OFF \
            -DWITH_TESTS=OFF

      # --- 5. OPTIMIZE (SLIM) ---
      - name: Filter RPMs
        run: |
          mkdir -p staging_rpms
          find rpmbuild/RPMS -name "*.rpm" \
            ! -name "*debuginfo*" ! -name "*debugsource*" \
            ! -name "*devel*" ! -name "*test*" ! -name "*static*" \
            -exec cp {} staging_rpms/ \;

      # --- 6. GENERATE DOCKERFILE ---
      - name: Generate Dockerfile
        run: |
          cat <<EOF > Dockerfile
          FROM quay.io/centos/centos:stream9
          RUN dnf install -y epel-release && /usr/bin/crb enable && dnf makecache
          RUN dnf install -y lvm2 python3 python3-pyyaml libibverbs librdmacm \
              libicu libaio nss nspr cryptsetup lua-devel && dnf clean all
          COPY staging_rpms/*.rpm /tmp/rpms/
          RUN dnf localinstall -y /tmp/rpms/*.rpm --skip-broken --setopt=install_weak_deps=False && \
              dnf clean all && rm -rf /tmp/rpms
          RUN mkdir -p /var/run/ceph /var/lib/ceph /var/log/ceph && \
              chmod 770 /var/run/ceph /var/lib/ceph /var/log/ceph
          ENTRYPOINT ["/usr/bin/ceph"]
          EOF

      # --- 7. PUSH TO GITHUB PACKAGES ---
      - name: Lowercase Repo Name
        run: echo "REPO_LOWER=${GITHUB_REPOSITORY,,}" >> ${GITHUB_ENV}

      - name: Login to GitHub Container Registry
        if: ${{ inputs.push_image }}
        uses: docker/login-action@v3
        with:
          registry: ghcr.io
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and Push
        if: ${{ inputs.push_image }}
        uses: docker/build-push-action@v5
        with:
          context: .
          file: Dockerfile
          push: true
          tags: |
            ghcr.io/${{ env.REPO_LOWER }}:${{ inputs.ceph_tag }}
            ghcr.io/${{ env.REPO_LOWER }}:latest
