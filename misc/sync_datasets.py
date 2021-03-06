"""A small utility for transferring features to/from the webserver.


NOTE: The dataset names are slightly different from the readme when using the tool. The
name map is given below:

README -> tool
-----------------
celeba -> celeba
AFLW_R -> aflw
AFLW_M -> aflw-mtfl
300w -> 300w

Example usage:
To fetch the 300w dataset, run the following in the project root folder:
python misc/sync_datasets.py --dataset 300w
"""
import os
import time
import subprocess
import argparse
from pathlib import Path


def upload_to_server(web_dir, dataset, webserver, root_feat_dir, refresh):
    # NOTE: The compression step will take a while. The last runs took:
    # celeba -> 02h00m23s

    server_dir = Path(web_dir) / "data" / "datasets"
    subprocess.call(["ssh", webserver, "mkdir -p", str(server_dir)])
    compressed_file = f"{dataset}.tar.gz"
    compressed_path = Path("data") / "webserver-files" / dataset / compressed_file
    if not compressed_path.parent.exists():
        compressed_path.parent.mkdir(exist_ok=True, parents=True)
    tar_include = Path("misc") / "datasets" / dataset.lower() / "tar_include.txt"
    compression_args = (f"tar --dereference --create --verbose"
                        f" --file={str(compressed_path)}"
                        f" --gzip  --files-from={tar_include}")
    print(f"running command {compression_args}")

    if not Path(compressed_path).exists() or refresh["compression"]:
        tic = time.time()
        # TODO(Samuel): Figure out why using subprocess introduces tarring problems
        os.system(compression_args)
        duration = time.strftime('%Hh%Mm%Ss', time.gmtime(time.time() - tic))
        print(f"Finished compressing dataset in {duration}")
    else:
        print(f"Found existing compressed file at {compressed_path}, skipping....")

    dest = f"{webserver}:{str(server_dir / compressed_file)}"
    rsync_args = ["rsync", "-av", "--progress", str(compressed_path), dest]
    if not refresh["server"]:
        rsync_args.insert(1, "--ignore-existing")
    tic = time.time()
    subprocess.call(rsync_args)
    duration = time.strftime('%Hh%Mm%Ss', time.gmtime(time.time() - tic))
    print(f"Finished transferring features in {duration}")


def fetch_from_server(dataset, root_url, refresh, purge_tar_file):
    local_data_dir = Path("data") / dataset
    if local_data_dir.exists() and not refresh["data"]:
        print(f"Found dataset directory at {str(local_data_dir)}, skipping")
        return

    local_data_dir.mkdir(exist_ok=True, parents=True)
    archive_name = f"{dataset}.tar.gz"
    local_archive = local_data_dir / archive_name
    if not local_archive.exists():
        src_url = f"{root_url}/datasets/{archive_name}"
        wget_args = ["wget", f"--output-document={str(local_archive)}", src_url]
        print(f"running command: {' '.join(wget_args)}")
        subprocess.call(wget_args)
    else:
        print(f"found archive at {local_archive}, skipping...")

    # unpack the archive and optionally clean up
    untar_args = ["tar", "-xvf", str(local_archive)]
    subprocess.call(untar_args)
    if purge_tar_file:
        local_archive.unlink()
    import ipdb; ipdb.set_trace()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True,
                        choices=["celeba", "aflw-recrop", "aflw-mtfl", "300w"])
    parser.add_argument("--action", default="fetch", choices=["upload", "fetch"])
    parser.add_argument("--webserver", default="login.robots.ox.ac.uk")
    parser.add_argument("--refresh_compression", action="store_true")
    parser.add_argument("--refresh_server", action="store_true")
    parser.add_argument("--refresh_data", action="store_true")
    parser.add_argument("--purge_tar_file", action="store_true")
    parser.add_argument("--web_dir", default="/projects/vgg/vgg/WWW/research/DVE")
    parser.add_argument(
        "--root_url", default="http://www.robots.ox.ac.uk/~vgg/research/DVE/data",
    )
    args = parser.parse_args()

    server_root_feat_dir = Path("data") / args.dataset / "symlinked-feats"
    refresh_targets = {
        "server": args.refresh_server,
        "compression": args.refresh_compression,
        "data": args.refresh_data,
    }

    if args.action == "upload":
        upload_to_server(
            web_dir=args.web_dir,
            dataset=args.dataset,
            refresh=refresh_targets,
            webserver=args.webserver,
            root_feat_dir=server_root_feat_dir,
        )
    elif args.action == "fetch":
        fetch_from_server(
            dataset=args.dataset,
            root_url=args.root_url,
            refresh=refresh_targets,
            purge_tar_file=args.purge_tar_file,
        )
    else:
        raise ValueError(f"unknown action: {args.action}")